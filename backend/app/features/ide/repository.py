"""Exercices, séances, exécutions et notes de l'IDE (phase 10). Les lectures qui précèdent une
écriture rafraîchissent la ligne (`populate_existing`) : deux requêtes qui se suivent voient l'état
commité par la précédente. Le commit appartient à l'appelant."""

import builtins
from datetime import datetime

from sqlalchemy import select

from app.db.models.ide import IdeExercise, IdeNote, IdeRun, IdeSession
from app.db.repository import UserScopedRepository


class ExerciseRepository(UserScopedRepository[IdeExercise]):
    model = IdeExercise

    async def newest_first(self) -> builtins.list[IdeExercise]:
        stmt = (
            select(IdeExercise)
            .where(IdeExercise.user_id == self.user_id)
            .order_by(IdeExercise.created_at.desc(), IdeExercise.id)
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())


class SessionRepository(UserScopedRepository[IdeSession]):
    model = IdeSession

    async def get_fresh(self, session_id: str) -> IdeSession | None:
        stmt = (
            select(IdeSession)
            .where(IdeSession.id == session_id, IdeSession.user_id == self.user_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def newest_first(self) -> builtins.list[IdeSession]:
        stmt = (
            select(IdeSession)
            .where(IdeSession.user_id == self.user_id)
            .order_by(IdeSession.updated_at.desc(), IdeSession.id)
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def passed_between(
        self, after: datetime | None, before: datetime | None, limit: int
    ) -> builtins.list[IdeSession]:
        """Les séances dont la première vérification réussie date de `[after, before]` (bornes
        incluses), la plus récente d'abord."""
        stmt = select(IdeSession).where(
            IdeSession.user_id == self.user_id, IdeSession.passed_at.is_not(None)
        )
        if after is not None:
            stmt = stmt.where(IdeSession.passed_at >= after)
        if before is not None:
            stmt = stmt.where(IdeSession.passed_at <= before)
        stmt = stmt.order_by(IdeSession.passed_at.desc(), IdeSession.id.desc()).limit(limit)
        return builtins.list((await self.session.execute(stmt)).scalars().all())


class RunRepository(UserScopedRepository[IdeRun]):
    model = IdeRun

    async def get_fresh(self, run_id: str) -> IdeRun | None:
        stmt = (
            select(IdeRun)
            .where(IdeRun.id == run_id, IdeRun.user_id == self.user_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def running(self) -> builtins.list[IdeRun]:
        """Les exécutions que le bac n'a pas encore rendues (au plus une par utilisatrice)."""
        stmt = (
            select(IdeRun)
            .where(IdeRun.user_id == self.user_id, IdeRun.status == "running")
            .order_by(IdeRun.created_at, IdeRun.id)
            .execution_options(populate_existing=True)
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())


class NoteRepository(UserScopedRepository[IdeNote]):
    model = IdeNote

    async def get_fresh(self, note_id: str) -> IdeNote | None:
        stmt = (
            select(IdeNote)
            .where(IdeNote.id == note_id, IdeNote.user_id == self.user_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def of_session(self, session_id: str) -> builtins.list[IdeNote]:
        """Les notes de la séance, les plus anciennes d'abord."""
        stmt = (
            select(IdeNote)
            .where(IdeNote.user_id == self.user_id, IdeNote.session_id == session_id)
            .order_by(IdeNote.created_at, IdeNote.id)
            .execution_options(populate_existing=True)
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def open_proposals(self, session_id: str) -> builtins.list[IdeNote]:
        """Les propositions de la séance encore ouvertes."""
        stmt = (
            select(IdeNote)
            .where(
                IdeNote.user_id == self.user_id,
                IdeNote.session_id == session_id,
                IdeNote.kind == "proposal",
                IdeNote.status == "open",
            )
            .execution_options(populate_existing=True)
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())
