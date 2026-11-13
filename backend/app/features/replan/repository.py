"""Lectures de la replanification (SPEC F13) : bilans hebdomadaires (lignes `weekly_review` du
journal, écrites par `capture.service.journal`), faits d'une semaine (tentatives de quiz notées,
sessions d'étude terminées, captures) et sessions `replan` lancées pour un bilan. Toutes filtrent
par `user_id`."""

import builtins
from collections.abc import Collection
from datetime import date, datetime

from sqlalchemy import func, select

from app.db.models.agents import AgentSession
from app.db.models.study import JournalEntry, Quiz, QuizAttempt, StudySession
from app.db.repository import UserScopedRepository

REVIEW_KIND = "weekly_review"


class ReviewRepository(UserScopedRepository[JournalEntry]):
    model = JournalEntry

    async def review(self, entry_id: str) -> JournalEntry | None:
        stmt = select(JournalEntry).where(
            JournalEntry.user_id == self.user_id,
            JournalEntry.id == entry_id,
            JournalEntry.kind == REVIEW_KIND,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def by_key(self, ref_key: str) -> JournalEntry | None:
        stmt = select(JournalEntry).where(
            JournalEntry.user_id == self.user_id, JournalEntry.ref_key == ref_key
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def texts(self, entry_ids: Collection[str]) -> dict[str, str]:
        """`entrée → texte` des bilans demandés (historique des versions)."""
        if not entry_ids:
            return {}
        stmt = select(JournalEntry.id, JournalEntry.text).where(
            JournalEntry.user_id == self.user_id,
            JournalEntry.id.in_(builtins.list(entry_ids)),
            JournalEntry.kind == REVIEW_KIND,
        )
        return {row[0]: row[1] for row in (await self.session.execute(stmt)).all()}

    async def captures(self, first: date, last: date) -> int:
        stmt = select(func.count()).where(
            JournalEntry.user_id == self.user_id,
            JournalEntry.kind == "capture",
            JournalEntry.occurred_on >= first,
            JournalEntry.occurred_on <= last,
        )
        return int((await self.session.execute(stmt)).scalar_one())


class FactsRepository(UserScopedRepository[QuizAttempt]):
    """Ce qui s'est passé pendant une semaine, entre deux instants UTC."""

    model = QuizAttempt

    async def quiz_scores(self, program_id: str, start: datetime, end: datetime) -> list[int]:
        stmt = (
            select(QuizAttempt.score)
            .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
            .where(
                QuizAttempt.user_id == self.user_id,
                Quiz.user_id == self.user_id,
                Quiz.program_id == program_id,
                QuizAttempt.status == "graded",
                QuizAttempt.score.is_not(None),
                QuizAttempt.graded_at >= start,
                QuizAttempt.graded_at < end,
            )
            .order_by(QuizAttempt.graded_at)
        )
        return [int(s) for s in (await self.session.execute(stmt)).scalars() if s is not None]

    async def study_minutes(self, program_id: str, start: datetime, end: datetime) -> int:
        stmt = select(func.coalesce(func.sum(StudySession.minutes), 0)).where(
            StudySession.user_id == self.user_id,
            StudySession.program_id == program_id,
            StudySession.status == "finished",
            StudySession.ended_at >= start,
            StudySession.ended_at < end,
        )
        return int((await self.session.execute(stmt)).scalar_one())


class ReplanSessionRepository(UserScopedRepository[AgentSession]):
    model = AgentSession

    async def launched_for(self, program_id: str, entry_id: str) -> bool:
        """Une session `replan` a-t-elle déjà été lancée pour ce bilan (quel que soit son sort) ?"""
        stmt = select(func.count()).where(
            AgentSession.user_id == self.user_id,
            AgentSession.graph == "replan",
            AgentSession.subject_type == "program",
            AgentSession.subject_id == program_id,
            AgentSession.input["review_entry_id"].as_string() == entry_id,
        )
        return int((await self.session.execute(stmt)).scalar_one()) > 0
