"""IDE exercises, sessions, runs and notes (phase 10). Reads that precede a write refresh the row
(`populate_existing`): two successive requests see the state committed by the earlier one. The
commit belongs to the caller."""

import builtins
from datetime import datetime
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.practice import RECENT_PRACTICE
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
        """Sessions whose first successful check falls within `[after, before]` (inclusive
        bounds), most recent first."""
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
        """The session's last run, `None` if there is none."""
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
        """The session's latest runs, most recent first."""
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

    async def recent_for_exercise(
        self, exercise_id: str, version: str | None, run_id: str | None = None
    ) -> builtins.list[tuple[IdeRun, str | None]]:
        scope = (
            select(IdeRun, IdeSession.exercise_version)
            .join(IdeSession, IdeSession.id == IdeRun.session_id)
            .where(
                IdeSession.user_id == self.user_id,
                IdeSession.exercise_id == exercise_id,
                IdeRun.user_id == self.user_id,
                IdeRun.kind == "check",
                IdeRun.origin == "app",
                IdeRun.status != "running",
            )
        )
        recent = scope.order_by(
            (IdeSession.exercise_version == version).desc(),
            IdeRun.created_at.desc(),
            IdeRun.id.desc(),
        ).limit(RECENT_PRACTICE)
        checks = [(run, fingerprint) for run, fingerprint in await self.session.execute(recent)]
        if run_id and all(run.id != run_id for run, _ in checks):
            picked = (await self.session.execute(scope.where(IdeRun.id == run_id))).one_or_none()
            if picked is not None:
                run, fingerprint = picked
                checks.append((run, fingerprint))
        return checks

    async def running(self) -> builtins.list[IdeRun]:
        """Runs the sandbox has not returned yet (at most one per user)."""
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
        """The session's notes, oldest first."""
        stmt = (
            select(IdeNote)
            .where(IdeNote.user_id == self.user_id, IdeNote.session_id == session_id)
            .order_by(IdeNote.created_at, IdeNote.id)
            .execution_options(populate_existing=True)
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def open_proposals(self, session_id: str) -> builtins.list[IdeNote]:
        """The session's proposals that are still open."""
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
    """The internal professor's notes: anti-repetition, grading, idle delay."""

    model = IdeNote

    async def of_professor(self, session_id: str) -> builtins.list[IdeNote]:
        """The professor's notes in the session, oldest first."""
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
    """The professor's tokens, read from the call log (`llm_calls`): a call's agent session carries
    the code session as its subject. A single source (retries and cut-off calls counted), never a
    counter to keep up to date."""

    def __init__(self, session: AsyncSession, user_id: str) -> None:
        self.session = session
        self.user_id = user_id

    def _sum(self) -> Select[Any]:
        return select(func.coalesce(func.sum(LlmCall.tokens_in + LlmCall.tokens_out), 0)).where(
            LlmCall.user_id == self.user_id, LlmCall.graph == TEACHER_GRAPH
        )

    async def of_session(self, ide_session_id: str) -> int:
        """Tokens (input + output) of the professor's calls in this code session."""
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
        """The professor's tokens since `moment` (start of the user's day)."""
        stmt = self._sum().where(LlmCall.created_at >= moment)
        return int((await self.session.execute(stmt)).scalar_one() or 0)
