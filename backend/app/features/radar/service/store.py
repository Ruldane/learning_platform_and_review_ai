"""Port du parcours `market_radar` (`RadarStore`, D159) sur la feature `radar` : implémentation
branchée par `bootstrap_agents.agent_ports(..., radar=...)`. Chaque appel ouvre ses propres
sessions de base, courtes ; la lecture d'une page se fait hors transaction.

Toutes les écritures d'un relevé (colonne JSON `postings`, compteurs) passent sous le verrou du
relevé : les cinq lectures simultanées d'un passage s'écrivent l'une après l'autre. Chacune est
**idempotente** (SPEC 9.4) : une page déjà lue (lien normalisé) est rendue sans relecture ni
recompte, une extraction déjà rangée n'est pas refaite. Une page qui ne se lit pas (site bloqué,
domaine exclu, lien refusé) n'est pas une erreur : `unreadable`, comptée par site.

Le poste, la zone, les liens, les sites et les textes sont des données personnelles ou du web :
jamais journalisés (17.2) ; les journaux portent des identifiants, des nombres et des codes."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.radar_port import MAX_READS, PostingPage, RadarContext, RadarSummary
from app.agents.tools.radar_schema import TEXT_MAX, RadarFinding, link_key
from app.core.errors import AppError
from app.db.models.daily import RadarRun
from app.features.ledger.service.ledger import safe_code
from app.features.radar.repository import RadarRunRepository
from app.features.radar.service.entries import (
    Entry,
    blocked_domains,
    count,
    domain_of,
    is_closed,
    is_extracted,
    page_of,
)
from app.features.radar.service.finalize import finalize_run
from app.features.radar.service.rules import salary_shown
from app.features.radar.service.runs import radar_run_not_found
from app.features.radar.service.runtime import RadarRuntime
from app.features.research.service.reading import read
from app.features.settings.service import SettingsService

logger = logging.getLogger(__name__)


def read_limit() -> AppError:
    return AppError(
        "radar_read_limit", f"Un relevé lit {MAX_READS} pages au plus : plafond atteint.", 409
    )


def _apply(row: RadarRun, entries: list[Entry]) -> None:
    """Range les entrées (nouvelle liste : la colonne JSON est vue modifiée) et les nombres."""
    counted = count(entries)
    row.postings = entries
    row.read_count, row.blocked_count = counted.read, counted.blocked
    row.not_postings, row.analyzed = counted.not_postings, counted.analyzed
    row.blocked_domains = blocked_domains(entries)


def _with_finding(entry: Entry, item: RadarFinding) -> Entry:
    """L'entrée enrichie de l'extraction ; le salaire n'est gardé que si ses nombres figurent dans
    le texte lu (la vérification du parcours est refaite : l'adaptateur ne la présume pas)."""
    if not item.is_job_posting:
        return entry | {"read": "not_posting"}
    return entry | {
        "title": item.title,
        "company": item.company,
        "level": item.level,
        "remote": item.remote,
        "salary": salary_shown(item.salary, str(entry.get("text", ""))),
        "skills": [{"name": skill.name, "required": skill.required} for skill in item.skills],
        "tools": list(item.tools),
    }


def _extracted_entries(
    entries: list[Entry], items: list[RadarFinding], failed_refs: list[str]
) -> list[Entry]:
    """Les entrées avec les extractions et les échecs rangés ; une entrée qui a déjà son issue (ou
    qui est bloquée) n'est jamais réécrite : le rejeu ne change rien."""
    out = [dict(entry) for entry in entries]
    position = {str(entry["ref"]): number for number, entry in enumerate(out)}
    for item in items:
        number = position.get(item.ref)
        if number is not None and not is_closed(out[number]):
            out[number] = _with_finding(out[number], item)
    for ref in failed_refs:
        number = position.get(ref)
        if number is not None and not is_closed(out[number]):
            out[number] = out[number] | {"read": "extract_failed"}
    return out


class AgentRadarStore:
    def __init__(self, runtime: RadarRuntime) -> None:
        self._rt = runtime

    async def _row(self, db: AsyncSession, user_id: str, run_id: str) -> RadarRun:
        row = await RadarRunRepository(db, user_id).get_fresh(run_id)
        if row is None:
            raise radar_run_not_found()
        return row

    async def context(self, user_id: str, run_id: str) -> RadarContext:
        async with self._rt.session_factory() as db:
            row = await self._row(db, user_id, run_id)
            entries: list[Entry] = list(row.postings)
            languages = tuple((await SettingsService(db, user_id).get()).search_languages)
            role, zone = row.role, row.zone
        return RadarContext(
            run_id=run_id,
            role=role,
            zone=zone,
            languages=languages,
            read=[page_of(entry) for entry in entries],
            extracted=frozenset(str(e["ref"]) for e in entries if is_extracted(e)),
            attempts=len(entries),
        )

    async def save_candidates(
        self, user_id: str, session_id: str, run_id: str, queries: int, urls: list[str]
    ) -> None:
        async with self._rt.run_lock(user_id, run_id), self._rt.session_factory() as db:
            row = await self._row(db, user_id, run_id)
            row.queries, row.candidates = queries, len(urls)
            await db.commit()
        logger.info("Candidats : relevé %s, %d requête(s), %d lien(s)", run_id, queries, len(urls))

    async def _known(self, user_id: str, run_id: str, key: str) -> PostingPage | None:
        async with self._rt.session_factory() as db:
            row = await self._row(db, user_id, run_id)
            for entry in row.postings:
                if entry.get("key") == key:
                    return page_of(entry)
        return None

    async def _fetch(self, user_id: str, url: str) -> tuple[bool, str]:
        """`(lisible, texte)` : cache, débit par domaine, garde SSRF et domaines exclus sont ceux
        de la recherche web (lecture hors session)."""
        try:
            outcome = await read(self._rt.research, user_id, None, url)
        except AppError as exc:  # lien refusé (`invalid_url`, `url_forbidden`) : page illisible
            logger.info("Lien refusé : utilisateur %s, code %s", user_id, exc.code)
            return False, ""
        return outcome.status == "ok", outcome.text[:TEXT_MAX]

    async def read_posting(
        self, user_id: str, session_id: str, run_id: str, url: str
    ) -> PostingPage:
        key = link_key(url) or url.strip()
        known = await self._known(user_id, run_id, key)
        if known is not None:
            return known
        readable, text = await self._fetch(user_id, url)
        async with self._rt.run_lock(user_id, run_id), self._rt.session_factory() as db:
            row = await self._row(db, user_id, run_id)
            entries: list[Entry] = [dict(entry) for entry in row.postings]
            for entry in entries:
                if entry.get("key") == key:  # une lecture simultanée du même lien a gagné
                    return page_of(entry)
            if len(entries) >= MAX_READS:
                raise read_limit()
            added: Entry = {
                "ref": f"p{len(entries) + 1}",
                "url": url,
                "key": key,
                "domain": domain_of(url),
                "read": "ok" if readable else "blocked",
                "text": text,
            }
            _apply(row, [*entries, added])
            await db.commit()
        logger.info("Page lue : relevé %s, repère %s, %s", run_id, added["ref"], added["read"])
        return page_of(added)

    async def save_extraction(
        self,
        user_id: str,
        session_id: str,
        run_id: str,
        items: list[RadarFinding],
        failed_refs: list[str],
    ) -> None:
        async with self._rt.run_lock(user_id, run_id), self._rt.session_factory() as db:
            row = await self._row(db, user_id, run_id)
            _apply(row, _extracted_entries(list(row.postings), items, failed_refs))
            await db.commit()
        logger.info(
            "Extraction : relevé %s, %d offre(s), %d en échec", run_id, len(items), len(failed_refs)
        )

    async def finalize(self, user_id: str, session_id: str, run_id: str) -> RadarSummary:
        return await finalize_run(self._rt, user_id, run_id)

    async def fail(self, user_id: str, session_id: str, run_id: str, code: str) -> None:
        async with self._rt.run_lock(user_id, run_id), self._rt.session_factory() as db:
            row = await self._row(db, user_id, run_id)
            if row.status == "running":
                row.status, row.error_code = "failed", safe_code(code)
                row.finished_at = self._rt.now()
                await db.commit()
        logger.info("Relevé en échec : relevé %s, code %s", run_id, safe_code(code))
