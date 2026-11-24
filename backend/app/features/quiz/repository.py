"""Quizzes, questions, attempts and review cards (D99, D101). Fresh reads
(`populate_existing`); contended writes are guarded in SQL (`UPDATE … WHERE` on the expected
state, `INSERT … ON CONFLICT DO NOTHING`): a double submission writes only once."""

import builtins
from collections.abc import Collection
from datetime import date, datetime
from typing import Any

from sqlalchemy import CursorResult, func, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.core.practice import RECENT_PRACTICE
from app.db.models.study import Flashcard, Quiz, QuizAttempt, QuizQuestion
from app.db.repository import UserScopedRepository


def _changed(result: Any) -> bool:
    return isinstance(result, CursorResult) and result.rowcount == 1


class QuizRepository(UserScopedRepository[Quiz]):
    model = Quiz

    async def get_fresh(self, quiz_id: str) -> Quiz | None:
        stmt = (
            select(Quiz)
            .where(Quiz.id == quiz_id, Quiz.user_id == self.user_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def by_module(self, module_id: str) -> Quiz | None:
        stmt = (
            select(Quiz)
            .where(Quiz.module_id == module_id, Quiz.user_id == self.user_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def for_program(self, program_id: str) -> builtins.list[Quiz]:
        stmt = (
            select(Quiz)
            .where(Quiz.program_id == program_id, Quiz.user_id == self.user_id)
            .execution_options(populate_existing=True)
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def mark_ready(self, quiz_id: str, session_id: str, title: str) -> bool:
        """Moves the quiz to `ready` unless it already is; true if this call did it."""
        stmt = (
            update(Quiz)
            .where(Quiz.id == quiz_id, Quiz.user_id == self.user_id, Quiz.status != "ready")
            .values(status="ready", session_id=session_id, failure_reason=None, title=title)
        )
        return _changed(await self.session.execute(stmt))

    async def mark_failed(self, quiz_id: str, reason: str) -> None:
        """Quiz marked failed, never a quiz already ready."""
        stmt = (
            update(Quiz)
            .where(Quiz.id == quiz_id, Quiz.user_id == self.user_id, Quiz.status != "ready")
            .values(status="failed", failure_reason=reason)
        )
        await self.session.execute(stmt)


class QuestionRepository(UserScopedRepository[QuizQuestion]):
    model = QuizQuestion

    async def for_quiz(self, quiz_id: str) -> builtins.list[QuizQuestion]:
        stmt = (
            select(QuizQuestion)
            .where(QuizQuestion.quiz_id == quiz_id, QuizQuestion.user_id == self.user_id)
            .order_by(QuizQuestion.rank)
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())


class AttemptRepository(UserScopedRepository[QuizAttempt]):
    model = QuizAttempt

    async def get_fresh(self, attempt_id: str) -> QuizAttempt | None:
        stmt = (
            select(QuizAttempt)
            .where(QuizAttempt.id == attempt_id, QuizAttempt.user_id == self.user_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def for_quizzes(self, quiz_ids: Collection[str]) -> builtins.list[QuizAttempt]:
        """Attempts of these quizzes, oldest first."""
        if not quiz_ids:
            return []
        stmt = (
            select(QuizAttempt)
            .where(
                QuizAttempt.user_id == self.user_id,
                QuizAttempt.quiz_id.in_(builtins.list(quiz_ids)),
            )
            .order_by(QuizAttempt.created_at, QuizAttempt.id)
            .execution_options(populate_existing=True)
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def recent_completed(self, quiz_id: str, version: str) -> builtins.list[QuizAttempt]:
        stmt = (
            select(QuizAttempt)
            .where(
                QuizAttempt.user_id == self.user_id,
                QuizAttempt.quiz_id == quiz_id,
                QuizAttempt.status.in_(("graded", "failed")),
            )
            .order_by(
                (QuizAttempt.question_version == version).desc(),
                QuizAttempt.created_at.desc(),
                QuizAttempt.id.desc(),
            )
            .limit(RECENT_PRACTICE)
        )
        return builtins.list((await self.session.execute(stmt)).scalars())

    async def graded_modules(self, module_ids: Collection[str]) -> set[str]:
        """Modules among `module_ids` whose quiz has at least one graded attempt."""
        if not module_ids:
            return set()
        stmt = (
            select(Quiz.module_id)
            .join(QuizAttempt, QuizAttempt.quiz_id == Quiz.id)
            .where(
                Quiz.user_id == self.user_id,
                QuizAttempt.user_id == self.user_id,
                QuizAttempt.status == "graded",
                Quiz.module_id.in_(builtins.list(module_ids)),
            )
        )
        return set((await self.session.execute(stmt)).scalars().all())

    async def claim_graded(self, attempt_id: str) -> bool:
        """`grading` → `graded`; true if this call did it (a replay gets false)."""
        stmt = (
            update(QuizAttempt)
            .where(
                QuizAttempt.id == attempt_id,
                QuizAttempt.user_id == self.user_id,
                QuizAttempt.status == "grading",
            )
            .values(status="graded")
        )
        return _changed(await self.session.execute(stmt))

    async def fail_grading(self, attempt_ids: Collection[str]) -> None:
        """Attempts still `grading` moved to failed (interrupted grading)."""
        if not attempt_ids:
            return
        stmt = (
            update(QuizAttempt)
            .where(
                QuizAttempt.user_id == self.user_id,
                QuizAttempt.id.in_(builtins.list(attempt_ids)),
                QuizAttempt.status == "grading",
            )
            .values(status="failed")
        )
        await self.session.execute(stmt)


class FlashcardRepository(UserScopedRepository[Flashcard]):
    model = Flashcard

    async def recent_quiz_errors(
        self, start: datetime, end: datetime
    ) -> builtins.list[tuple[str, str]]:
        stmt = (
            select(Flashcard.front, Flashcard.back)
            .where(
                Flashcard.user_id == self.user_id,
                Flashcard.source == "quiz",
                Flashcard.created_at >= start,
                Flashcard.created_at < end,
            )
            .order_by(Flashcard.created_at.desc())
            .limit(5)
        )
        return [(front, back) for front, back in (await self.session.execute(stmt)).all()]

    async def insert_once(self, **fields: Any) -> bool:
        """Writes the card if its front (`front_hash`) is new; true if it was created."""
        stmt = (
            sqlite_insert(Flashcard)
            .values(user_id=self.user_id, **fields)
            .on_conflict_do_nothing(index_elements=["user_id", "front_hash"])
            .returning(Flashcard.id)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none() is not None

    async def get_fresh(self, card_id: str) -> Flashcard | None:
        stmt = (
            select(Flashcard)
            .where(Flashcard.id == card_id, Flashcard.user_id == self.user_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def due(self, today: date, limit: int) -> builtins.list[Flashcard]:
        """Due cards (due date ≤ `today`), most overdue first, at most `limit`."""
        if limit <= 0:
            return []
        stmt = (
            select(Flashcard)
            .where(Flashcard.user_id == self.user_id, Flashcard.due_date <= today)
            .order_by(Flashcard.due_date, Flashcard.created_at, Flashcard.id)
            .limit(limit)
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def due_skills(self, today: date) -> builtins.list[str]:
        """The skills (as written) of the due cards, once each."""
        stmt = (
            select(Flashcard.skill)
            .where(
                Flashcard.user_id == self.user_id,
                Flashcard.due_date <= today,
                Flashcard.skill.is_not(None),
            )
            .distinct()
        )
        return [str(skill) for skill in (await self.session.execute(stmt)).scalars()]

    async def count_due(self, today: date) -> int:
        stmt = select(func.count()).where(
            Flashcard.user_id == self.user_id, Flashcard.due_date <= today
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def count_reviewed(self, today: date) -> int:
        stmt = select(func.count()).where(
            Flashcard.user_id == self.user_id, Flashcard.last_reviewed_on == today
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def claim_review(self, card: Flashcard, today: date, step: int, due: date) -> bool:
        """Review guarded by the due date: the card must be due (≤ `today`); true if this call
        reviewed it (a second review finds it already pushed back)."""
        stmt = (
            update(Flashcard)
            .where(
                Flashcard.id == card.id,
                Flashcard.user_id == self.user_id,
                Flashcard.due_date <= today,
            )
            .values(updated_at=Flashcard.updated_at)
        )
        if not _changed(await self.session.execute(stmt)):
            return False
        # The ORM write is recorded in the history of the response relayed by Nod.
        card.step, card.due_date, card.last_reviewed_on = step, due, today
        await self.session.flush()
        return True
