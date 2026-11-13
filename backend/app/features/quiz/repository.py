"""Quiz, questions, tentatives et fiches de révision (D99, D101). Lectures fraîches
(`populate_existing`) ; les écritures disputées sont gardées en SQL (`UPDATE … WHERE` sur l'état
attendu, `INSERT … ON CONFLICT DO NOTHING`) : un double envoi n'écrit qu'une fois."""

import builtins
from collections.abc import Collection
from datetime import date
from typing import Any

from sqlalchemy import CursorResult, func, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

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
        """Passe le quiz à `ready` s'il ne l'est pas déjà ; vrai si c'est cet appel."""
        stmt = (
            update(Quiz)
            .where(Quiz.id == quiz_id, Quiz.user_id == self.user_id, Quiz.status != "ready")
            .values(status="ready", session_id=session_id, failure_reason=None, title=title)
        )
        return _changed(await self.session.execute(stmt))

    async def mark_failed(self, quiz_id: str, reason: str) -> None:
        """Quiz en échec, jamais un quiz déjà prêt."""
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
        """Tentatives de ces quiz, de la plus ancienne à la plus récente."""
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

    async def graded_modules(self, module_ids: Collection[str]) -> set[str]:
        """Modules parmi `module_ids` dont le quiz a au moins une tentative notée."""
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
        """`grading` → `graded` ; vrai si c'est cet appel (un rejeu reçoit faux)."""
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
        """Tentatives encore `grading` passées en échec (notation interrompue)."""
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

    async def insert_once(self, **fields: Any) -> bool:
        """Écrit la fiche si son recto (`front_hash`) est nouveau ; vrai si elle est créée."""
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
        """Fiches dues (échéance ≤ `today`), les plus en retard d'abord, `limit` au plus."""
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
        """Les compétences (telles qu'écrites) des fiches dues, une fois chacune."""
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

    async def claim_review(self, card_id: str, today: date, step: int, due: date) -> bool:
        """Avis gardé par l'échéance : la fiche doit être due (≤ `today`) ; vrai si c'est cet
        appel qui l'a revue (un second avis la trouve déjà repoussée)."""
        stmt = (
            update(Flashcard)
            .where(
                Flashcard.id == card_id,
                Flashcard.user_id == self.user_id,
                Flashcard.due_date <= today,
            )
            .values(step=step, due_date=due, last_reviewed_on=today)
        )
        return _changed(await self.session.execute(stmt))
