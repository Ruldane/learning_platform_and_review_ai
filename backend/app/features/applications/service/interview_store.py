"""Mock interview port (`InterviewStore`, D145, D146) on the `applications` feature:
implementation wired by `bootstrap_agents.agent_ports(..., interviews=...)`. Each call opens its
own short database session.

- `context`: read-only (`interview_context`). 404 `interview_not_found` (the interview is not
  the user's), 409 `profile_required`.
- `save_result`: **idempotent per session**, under the interviews lock: an interview that is no
  longer `running` (replay after a stop, SPEC 9.4) is never rewritten. `debrief=None` without
  any exchange: `stopped` (nothing else); `debrief=None` with exchanges: `debrief_failed`
  (answers kept, no debrief, no cards, no event); otherwise `done`: exchanges, debrief (with
  `flags` and `cards_created`, stored with it), review cards (`quiz.service.cards.add_cards`,
  source `interview`, due tomorrow, never a skill: the text comes from the model) and, if the
  interview has a record, the `interview` event of the timeline, in the same transaction.

Logs: ids, statuses and numbers only (17.2)."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.interview_schema import Debrief, Exchange, InterviewContext
from app.agents.tools.study_schema import CardDraft
from app.agents.tools.system_design_port import (
    SystemDesignContext,
    SystemDesignReview,
    SystemDesignSubmission,
)
from app.core.clock import local_today
from app.db.models.applications import Interview
from app.features.applications.repository import ApplicationRepository, EventRepository
from app.features.applications.service.interview_context import build_context
from app.features.applications.service.interviews import interview_lock, interview_row
from app.features.applications.service.runtime import ApplicationsRuntime
from app.features.applications.service.system_design import freeze, save_review
from app.features.postings.service.duplicates import zone_of
from app.features.quiz.service.cards import NewCard, add_cards

logger = logging.getLogger(__name__)

MODE_LABELS = {
    "behavioral": "comportemental",
    "technical": "technique",
    "case": "case study",
    "mixed": "mixte",
}


def timeline_text(row: Interview, cards: int) -> str:
    label = MODE_LABELS.get(row.mode, row.mode)
    return (
        f"Mock interview ({label}, {row.duration_min} min) finished: debrief available, "
        f"{cards} review card(s) created."
    )


class AgentInterviewStore:
    def __init__(self, runtime: ApplicationsRuntime) -> None:
        self._rt = runtime

    async def freeze_design(
        self, user_id: str, session_id: str, interview_id: str, submission: SystemDesignSubmission
    ) -> SystemDesignContext:
        return await freeze(self._rt, user_id, session_id, interview_id, submission)

    async def save_design_review(
        self, user_id: str, session_id: str, interview_id: str, review: SystemDesignReview
    ) -> None:
        await save_review(self._rt, user_id, session_id, interview_id, review)

    async def context(self, user_id: str, interview_id: str) -> InterviewContext:
        async with self._rt.session_factory() as db:
            row = await interview_row(db, user_id, interview_id)
        return await build_context(self._rt, user_id, row)

    async def save_result(
        self,
        user_id: str,
        session_id: str,
        interview_id: str,
        exchanges: list[Exchange],
        debrief: Debrief | None,
        flags: list[str],
        cards: list[CardDraft],
    ) -> None:
        rt = self._rt
        async with interview_lock(rt, user_id), rt.session_factory() as db:
            row = await interview_row(db, user_id, interview_id)
            if row.status != "running":
                return  # replay: the outcome of the session is already stored
            row.exchanges = [item.model_dump(mode="json") for item in exchanges]
            created = 0
            if debrief is None:
                row.status = "debrief_failed" if exchanges else "stopped"
            else:
                created = await self._write_debrief(db, user_id, row, debrief, flags, cards)
            await db.commit()
            status = row.status
        logger.info(
            "Interview stored: user %s, interview %s, session %s, status %s, "
            "%d exchange(s), %d card(s)",
            user_id,
            interview_id,
            session_id,
            status,
            len(exchanges),
            created,
        )

    async def _write_debrief(
        self,
        db: AsyncSession,
        user_id: str,
        row: Interview,
        debrief: Debrief,
        flags: list[str],
        cards: list[CardDraft],
    ) -> int:
        """Debrief, review cards and timeline event; returns the number of cards created."""
        rt = self._rt
        today = local_today(await zone_of(db, user_id), rt.now())
        new = [NewCard(c.front, c.back, None, None, "interview", row.id) for c in cards]
        created = await add_cards(db, user_id, new, today)
        row.debrief = {
            **debrief.model_dump(mode="json"),
            "flags": list(flags),
            "cards_created": created,
        }
        row.status = "done"
        application = None
        if row.application_id is not None:
            application = await ApplicationRepository(db, user_id).get(row.application_id)
        if application is not None:
            await EventRepository(db, user_id).add(
                application_id=application.id,
                kind="interview",
                at=rt.now(),
                text=timeline_text(row, created),
                ref_id=row.id,
            )
        return created
