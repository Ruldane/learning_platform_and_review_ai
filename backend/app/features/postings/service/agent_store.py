"""Posting analysis port (`GapStore`, D121) on the `postings` feature: implementation wired by
`bootstrap_agents.agent_ports(..., gap=...)`. Each call opens its own short database sessions;
no transaction is open during vectorization (D66).

- `save_analysis`: `UPDATE … WHERE analysis IS NULL` (the first analysis wins), title, company
  and its key, `ready` status, `posting` memory item (title, company, frozen text) written by
  `MemoryService.write` then indexed; then probable and possible duplicates, stored on both
  sides and returned even on replay. The reference list is not touched.
- `save_gap`: `gap` = `{matches, session_id}`, no effect for the same session; in the same
  transaction, the needs left without a match enter the reference list (`upsert_catalog`,
  the posting's domain, otherwise `DEFAULT_DOMAIN`, P20). Rows and score recomputed (`gap_rows`).

A posting's text is never logged: ids and numbers only."""

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
REASON = "Saved the text of a posting added by January."
DEFAULT_DOMAIN = "Other"  # what the map shows for a skill without a domain
_TITLE_MAX = 200
_REASON_MAX = 300
_MIN_DOMAIN = 2


def not_analyzed() -> AppError:
    return AppError("posting_not_analyzed", "This posting has not been analyzed yet.", 409)


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
        await index_capture(self._memory, user_id, item_id)  # before the duplicates search
        async with self._factory() as db:
            posting = await self._fresh(db, user_id, posting_id)
            hits = await find_duplicates(db, self._memory, user_id, posting)
        async with self._factory() as db:
            posting = await self._fresh(db, user_id, posting_id)
            await store_duplicates(db, user_id, posting, hits)
            await db.commit()
        logger.info(
            "Posting analysis stored: user %s, posting %s, first %s, item %s, %d doublon(s)",
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
        """The `posting` item (same content already there: the existing one); not indexed, not
        committed."""
        analysis = PostingAnalysis.model_validate(posting.analysis)
        draft = WriteDraft(
            kind="posting",
            title=item_title(analysis),
            text=posting.text,
            author=AUTHOR,
            reason=REASON,
            tags=("posting",),
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
        logger.info("Posting refused: user %s, posting %s", user_id, posting_id)

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
                "Gap stored: user %s, posting %s, session %s, score %d, %d row(s)",
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
        """The analysis's learnable needs without a match enter the reference list (without a
        level); a need outside the scope of a program ("Driver's license", "Master's degree")
        does not."""
        analysis = PostingAnalysis.model_validate(posting.analysis)
        matched = {normalize_skill_name(m.need) for m in matches if m.known}
        drafts = [
            SkillDraft(name=need.name, domain=_domain(need.domain), synonyms=[])
            for need in analysis.skills
            if need.learnable and normalize_skill_name(need.name) not in matched
        ]
        if drafts:
            await SkillsService(db, user_id).upsert_catalog(drafts, [])
