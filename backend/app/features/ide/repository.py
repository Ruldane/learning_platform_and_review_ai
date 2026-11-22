"""Exercices, séances, exécutions et notes de l'IDE (phase 10). Les lectures qui précèdent une
écriture rafraîchissent la ligne (`populate_existing`) : deux requêtes qui se suivent voient l'état
commité par la précédente. Le commit appartient à l'appelant."""

import builtins
from datetime import datetime
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agents import AgentSession, LlmCall
from app.db.models.ide import IdeExercise, IdeNote, IdePreference, IdeRun, IdeSession
from app.db.repository import UserScopedRepository

TEACHER_GRAPH = "ide_teacher"
TEACHER_SUBJECT = "ide_session"


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

    async def pending_notebook(self, session_id: str, path: str) -> IdeRun | None:
        stmt = (
            select(IdeRun)
            .where(
                IdeRun.user_id == self.user_id,
                IdeRun.session_id == session_id,
                IdeRun.kind == "notebook",
                IdeRun.notebook_cell["path"].as_string() == path,
            )
            .order_by(IdeRun.created_at.desc(), IdeRun.id.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_fresh(self, run_id: str) -> IdeRun | None:
        stmt = (
            select(IdeRun)
            .where(IdeRun.id == run_id, IdeRun.user_id == self.user_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def latest_of_session(self, session_id: str) -> IdeRun | None:
        """La dernière exécution de la séance, `None` s'il n'y en a pas."""
        stmt = (
            select(IdeRun)
            .where(
                IdeRun.user_id == self.user_id,
                IdeRun.session_id == session_id,
                IdeRun.kind.in_(("run", "check")),
            )
            .order_by(IdeRun.created_at.desc(), IdeRun.id.desc())
            .limit(1)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def recent_of_session(self, session_id: str, limit: int) -> builtins.list[IdeRun]:
        """Les dernières exécutions de la séance, la plus récente d'abord."""
        stmt = (
            select(IdeRun)
            .where(
                IdeRun.user_id == self.user_id,
                IdeRun.session_id == session_id,
                IdeRun.kind.in_(("run", "check")),
            )
            .order_by(IdeRun.created_at.desc(), IdeRun.id.desc())
            .limit(limit)
            .execution_options(populate_existing=True)
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

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


class ProfessorNoteRepository(UserScopedRepository[IdeNote]):
    """Les notes du professeur interne : anti-répétition, gradation, délai d'inactivité."""

    model = IdeNote

    async def of_professor(self, session_id: str) -> builtins.list[IdeNote]:
        """Les notes du professeur de la séance, les plus anciennes d'abord."""
        stmt = (
            select(IdeNote)
            .where(
                IdeNote.user_id == self.user_id,
                IdeNote.session_id == session_id,
                IdeNote.author == "professor",
            )
            .order_by(IdeNote.created_at, IdeNote.id)
            .execution_options(populate_existing=True)
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())


class PreferenceRepository(UserScopedRepository[IdePreference]):
    model = IdePreference

    async def mine(self) -> IdePreference | None:
        stmt = (
            select(IdePreference)
            .where(IdePreference.user_id == self.user_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()


class TeacherUsageRepository:
    """Les jetons du professeur, lus dans le journal des appels (`llm_calls`) : la séance d'agents
    d'un appel porte la séance de code en sujet. Une seule source (retentatives et appels coupés
    comptés), jamais un compteur à tenir à jour."""

    def __init__(self, session: AsyncSession, user_id: str) -> None:
        self.session = session
        self.user_id = user_id

    def _sum(self) -> Select[Any]:
        return select(func.coalesce(func.sum(LlmCall.tokens_in + LlmCall.tokens_out), 0)).where(
            LlmCall.user_id == self.user_id, LlmCall.graph == TEACHER_GRAPH
        )

    async def of_session(self, ide_session_id: str) -> int:
        """Les jetons (entrée + sortie) des appels du professeur dans cette séance de code."""
        stmt = self._sum().where(
            LlmCall.session_id.in_(
                select(AgentSession.id).where(
                    AgentSession.user_id == self.user_id,
                    AgentSession.graph == TEACHER_GRAPH,
                    AgentSession.subject_type == TEACHER_SUBJECT,
                    AgentSession.subject_id == ide_session_id,
                )
            )
        )
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def since(self, moment: datetime) -> int:
        """Les jetons du professeur depuis `moment` (début du jour de l'utilisatrice)."""
        stmt = self._sum().where(LlmCall.created_at >= moment)
        return int((await self.session.execute(stmt)).scalar_one() or 0)
