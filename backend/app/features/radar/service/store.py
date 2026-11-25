"""Port of the `market_radar` flow (`RadarStore`, D159) on the `radar` feature: implementation
wired by `bootstrap_agents.agent_ports(..., radar=...)`. Each call opens its own short
database sessions; reading a page happens outside a transaction.

All the writes of a run (JSON column `postings`, counters) go under the run's lock: the five
simultaneous reads of a pass are written one after the other. Each is **idempotent** (SPEC
9.4): an already read page (normalized link) is returned without re-reading or recounting, an
already stored extraction is not redone. A page that cannot be read (blocked site, excluded
domain, refused link) is not an error: `unreadable`, counted per site.

The role, the zone, the links, the sites and the texts are personal or web data: never logged
(17.2); the logs carry ids, numbers and codes."""

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
        "radar_read_limit", f"This Radar run has reached its limit of {MAX_READS} pages.", 409
    )


def _apply(row: RadarRun, entries: list[Entry]) -> None:
    """Stores the entries (new list: the JSON column is seen as modified) and the numbers."""
    counted = count(entries)
    row.postings = entries
    row.read_count, row.blocked_count = counted.read, counted.blocked
    row.not_postings, row.analyzed = counted.not_postings, counted.analyzed
    row.blocked_domains = blocked_domains(entries)


def _with_finding(entry: Entry, item: RadarFinding) -> Entry:
    """The entry enriched with the extraction; the salary is only kept if its numbers appear in
    the text read (the flow's check is redone: the adapter does not presume it)."""
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
    """The entries with the extractions and failures stored; an entry that already has its
    outcome (or that is blocked) is never rewritten: the replay changes nothing."""
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
        logger.info("Candidates: run %s, %d query(ies), %d link(s)", run_id, queries, len(urls))

    async def _known(self, user_id: str, run_id: str, key: str) -> PostingPage | None:
        async with self._rt.session_factory() as db:
            row = await self._row(db, user_id, run_id)
            for entry in row.postings:
                if entry.get("key") == key:
                    return page_of(entry)
        return None

    async def _fetch(self, user_id: str, url: str) -> tuple[bool, str]:
        """`(readable, text)`: cache, per-domain rate, SSRF guard and excluded domains are those
        of the web search (read outside a session)."""
        try:
            outcome = await read(self._rt.research, user_id, None, url)
        except AppError as exc:  # link refused (`invalid_url`, `url_forbidden`): unreadable page
            logger.info("Link refused: user %s, code %s", user_id, exc.code)
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
                if entry.get("key") == key:  # a simultaneous read of the same link won
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
        logger.info("Page read: run %s, ref %s, %s", run_id, added["ref"], added["read"])
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
            "Extraction: run %s, %d posting(s), %d failed", run_id, len(items), len(failed_refs)
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
        logger.info("Run failed: run %s, code %s", run_id, safe_code(code))
