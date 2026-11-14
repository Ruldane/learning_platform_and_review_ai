"""Port de l'analyse d'offre (`GapStore`, D121) sur la feature `postings` : implémentation branchée
par `bootstrap_agents.agent_ports(..., gap=...)`. Chaque appel ouvre ses propres sessions de base,
courtes ; aucune transaction n'est ouverte pendant la vectorisation (D66).

- `save_analysis` : `UPDATE … WHERE analysis IS NULL` (la première analyse gagne), titre,
  entreprise et sa clé, statut `ready`, élément de mémoire `offre` (titre, entreprise, texte figé)
  écrit par `MemoryService.write` puis indexé ; puis doublons probables et possibles, rangés
  des deux côtés et rendus même au rejeu. Le référentiel n'est pas touché.
- `save_gap` : `gap` = `{matches, session_id}`, sans effet pour une même session ; dans la même
  transaction, les besoins restés sans rattachement entrent au référentiel (`upsert_catalog`,
  domaine de l'offre, sinon `DEFAULT_DOMAIN`, P20). Lignes et score recalculés (`gap_rows`).

Le texte d'une offre n'est jamais journalisé : identifiants et nombres seulement."""

import logging
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.tools.gap_port import (
    AnalysisSaved,
    GapSaved,
    KnownSkill,
    PostingView,
    SkillMatch,
    gap_result,
    ordered_known,
)
from app.agents.tools.plan_schema import SkillDraft
from app.agents.tools.posting_schema import PostingAnalysis
from app.core.errors import AppError
from app.core.skills import normalize_skill_name
from app.db.models.postings import JobPosting, PostingStatus
from app.features.gap.service.rows import gap_rows
from app.features.gap.service.score import match_score
from app.features.memory.service.captured import index_capture
from app.features.memory.service.items import MemoryService
from app.features.memory.service.rules import WriteDraft
from app.features.memory.service.runtime import MemoryRuntime
from app.features.postings.repository import PostingRepository
from app.features.postings.service.duplicates import find_duplicates, not_found, store_duplicates
from app.features.postings.service.rules import company_key
from app.features.skills.service import SkillsService

logger = logging.getLogger(__name__)

AUTHOR = "analyst"
REASON = "Offre ajoutée par January : copie figée de son texte."
DEFAULT_DOMAIN = "Autres"  # celui que la carte montre pour une compétence sans domaine
_TITLE_MAX = 200
_REASON_MAX = 300
_MIN_DOMAIN = 2


def not_analyzed() -> AppError:
    return AppError("posting_not_analyzed", "Cette offre n'est pas encore analysée.", 409)


def _domain(domain: str | None) -> str:
    cleaned = (domain or "").strip()
    return cleaned if len(cleaned) >= _MIN_DOMAIN else DEFAULT_DOMAIN


def item_title(analysis: PostingAnalysis) -> str:
    company = (analysis.company or "").strip()
    return f"{analysis.title} — {company}" if company else analysis.title


class AgentGapStore:
    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession], memory: MemoryRuntime
    ) -> None:
        self._factory = session_factory
        self._memory = memory

    async def _fresh(self, db: AsyncSession, user_id: str, posting_id: str) -> JobPosting:
        posting = await PostingRepository(db, user_id).get_fresh(posting_id)
        if posting is None:
            raise not_found()
        return posting

    async def posting(self, user_id: str, posting_id: str) -> PostingView:
        async with self._factory() as db:
            row = await self._fresh(db, user_id, posting_id)
            analysis = PostingAnalysis.model_validate(row.analysis) if row.analysis else None
            status: PostingStatus = row.status  # type: ignore[assignment]  # colonne contrainte
            return PostingView(row.id, row.text, row.url, analysis, status)

    async def save_analysis(
        self, user_id: str, session_id: str, posting_id: str, analysis: PostingAnalysis
    ) -> AnalysisSaved:
        company = (analysis.company or "").strip() or None
        async with self._factory() as db:
            await self._fresh(db, user_id, posting_id)
            first = await PostingRepository(db, user_id).claim_analysis(
                posting_id,
                analysis=analysis.model_dump(mode="json"),
                title=analysis.title[:_TITLE_MAX],
                company=company[:_TITLE_MAX] if company else None,
                company_norm=(company_key(company) or None) if company else None,
                status="ready",
                failure_reason=None,
            )
            posting = await self._fresh(db, user_id, posting_id)
            stored = PostingAnalysis.model_validate(posting.analysis)
            if posting.memory_item_id is None:
                posting.memory_item_id = await self._write_item(db, user_id, session_id, posting)
            item_id = posting.memory_item_id
            await db.commit()
        await index_capture(self._memory, user_id, item_id)  # avant la recherche des doublons
        async with self._factory() as db:
            posting = await self._fresh(db, user_id, posting_id)
            hits = await find_duplicates(db, self._memory, user_id, posting)
        async with self._factory() as db:
            posting = await self._fresh(db, user_id, posting_id)
            await store_duplicates(db, user_id, posting, hits)
            await db.commit()
        logger.info(
            "Analyse d'offre rangée : utilisateur %s, offre %s, première %s, élément %s, "
            "%d doublon(s)",
            user_id,
            posting_id,
            first,
            item_id,
            len(hits),
        )
        return AnalysisSaved(posting_id, stored, hits, first)

    async def _write_item(
        self, db: AsyncSession, user_id: str, session_id: str, posting: JobPosting
    ) -> str:
        """L'élément `offre` (même contenu déjà là : l'existant), non indexé ni commité."""
        analysis = PostingAnalysis.model_validate(posting.analysis)
        draft = WriteDraft(
            kind="offre",
            title=item_title(analysis),
            text=posting.text,
            author=AUTHOR,
            reason=REASON,
            tags=("offre",),
            session_id=session_id,
        )
        return (await MemoryService(db, user_id, self._memory).write(draft, index=False)).item.id

    async def reject(self, user_id: str, posting_id: str, reason: str) -> None:
        async with self._factory() as db:
            posting = await self._fresh(db, user_id, posting_id)
            if posting.status == "rejected":
                return
            posting.status = "rejected"
            posting.failure_reason = reason.strip()[:_REASON_MAX] or None
            await db.commit()
        logger.info("Offre refusée : utilisateur %s, offre %s", user_id, posting_id)

    async def known_skills(self, user_id: str) -> list[KnownSkill]:
        async with self._factory() as db:
            catalog = await SkillsService(db, user_id).catalog()
        return ordered_known([KnownSkill(name, level) for name, level in catalog])

    async def save_gap(
        self, user_id: str, session_id: str, posting_id: str, matches: Sequence[SkillMatch]
    ) -> GapSaved:
        async with self._factory() as db:
            posting = await self._fresh(db, user_id, posting_id)
            if posting.analysis is None:
                raise not_analyzed()
            written = (posting.gap or {}).get("session_id") != session_id
            if written:
                posting.gap = dict(gap_result(session_id, matches))
                await self._add_unmatched(db, user_id, posting, matches)
                await db.commit()
                posting = await self._fresh(db, user_id, posting_id)
            rows = [row for row in await gap_rows(db, user_id, posting) if row.source == "posting"]
        absent = [row for row in rows if row.level is None]
        saved = GapSaved(match_score(rows), len(rows), len(absent), sum(r.required for r in absent))
        if written:
            logger.info(
                "Écart rangé : utilisateur %s, offre %s, session %s, score %d, %d ligne(s)",
                user_id,
                posting_id,
                session_id,
                saved.score,
                saved.rows,
            )
        return saved

    async def _add_unmatched(
        self, db: AsyncSession, user_id: str, posting: JobPosting, matches: Sequence[SkillMatch]
    ) -> None:
        """Les besoins apprenables de l'analyse sans rattachement entrent au référentiel (sans
        niveau) ; un besoin hors du champ d'un programme (« Permis B », « Bac+5 ») n'y entre pas."""
        analysis = PostingAnalysis.model_validate(posting.analysis)
        matched = {normalize_skill_name(m.need) for m in matches if m.known}
        drafts = [
            SkillDraft(name=need.name, domain=_domain(need.domain), synonyms=[])
            for need in analysis.skills
            if need.learnable and normalize_skill_name(need.name) not in matched
        ]
        if drafts:
            await SkillsService(db, user_id).upsert_catalog(drafts, [])
