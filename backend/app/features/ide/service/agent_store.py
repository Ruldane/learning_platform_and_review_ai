"""The IDE port as seen by the agents (10.A3, `IdeStore`): what the professor reads and writes,
and the verification of the exercises generated in the sandbox. Each call opens its own database
session (the nodes run outside a request); the professor writes through `IdeService` under the
internal caller "professor": same validations and same notes table as Claude (P8). Nothing the
user's code contains is logged."""

import asyncio
import logging
from time import monotonic
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.tools.ide_port import NoteView, RunView, TeachInputs, Verification
from app.agents.tools.ide_schema import ExerciseDraft, TeacherNote
from app.core.errors import AppError
from app.core.providers import Providers
from app.db.models.ide import IdeNote
from app.features.ide.repository import (
    ExerciseRepository,
    NoteRepository,
    PreferenceRepository,
    RunRepository,
)
from app.features.ide.schemas import ExerciseIn, NoteIn
from app.features.ide.service import IdeService, sessions
from app.features.ide.service.context import IdeContext
from app.features.ide.service.teaching import PROFESSOR
from app.providers.sandbox.base import CodeSandbox, SandboxJob, UnknownRun

logger = logging.getLogger(__name__)

NOTES_SEEN = 30  # the notes re-read (the last 12 messages are drawn from them, references excluded)
VERIFY_TIMEOUT_S = 15  # real duration requested from the sandbox for an exercise's tests
VERIFY_WAIT_S = 40.0  # total wait for the result (queue included)
POLL_S = 0.3
STALE_CODES = frozenset({"note_stale", "note_invalid"})


def _view(note: IdeNote) -> NoteView:
    return NoteView(
        id=note.id,
        kind=note.kind,
        author=note.author,
        level=note.level,
        file_path=note.file_path,
        line_start=note.line_start,
        text=note.content,
        error_key=note.error_key,
    )


class AgentIdeStore:
    """`providers`: read on each call (the sandbox is set by the composition, or by a
    test)."""

    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession], providers: Providers
    ) -> None:
        self._factory = session_factory
        self._providers = providers

    def _ctx(self, db: AsyncSession, user_id: str) -> IdeContext:
        return IdeContext(db, user_id, self._providers.sandbox, PROFESSOR)

    async def teacher_inputs(
        self, user_id: str, ide_session_id: str, run_id: str | None
    ) -> TeachInputs:
        async with self._factory() as db:
            session = await sessions.get(self._ctx(db, user_id), ide_session_id)
            statement = None
            if session.exercise_id is not None:  # deleted since: the session keeps its title
                exercise = await ExerciseRepository(db, user_id).get(session.exercise_id)
                statement = exercise.statement if exercise is not None else None
            runs = RunRepository(db, user_id)
            run = await runs.get_fresh(run_id) if run_id else None
            if run is None or run.session_id != session.id:
                run = await runs.latest_of_session(session.id)
            prefs = await PreferenceRepository(db, user_id).mine()
            rows = await NoteRepository(db, user_id).of_session(session.id)
            return TeachInputs(
                title=session.title,
                statement=statement,
                files={str(path): str(text) for path, text in session.files.items()},
                entry=session.entry,
                passed=session.passed,
                style="pair" if prefs is not None and prefs.teacher_style == "pair" else "guide",
                run=None
                if run is None
                else RunView(
                    id=run.id,
                    kind=run.kind,
                    status=run.status,
                    exit_code=run.exit_code,
                    output=run.output,
                    error_signature=run.error_signature,
                ),
                notes=[_view(row) for row in rows[-NOTES_SEEN:]],
            )

    async def save_note(
        self,
        user_id: str,
        ide_session_id: str,
        note: TeacherNote,
        *,
        base_hash: str | None,
        error_key: str | None,
    ) -> str | None:
        """Stores the note; `None` if the code has changed since the read (stale proposal) or if
        the note is no longer valid: nothing is stored."""
        async with self._factory() as db:
            service = IdeService(db, user_id, None, PROFESSOR)
            try:
                data = NoteIn(
                    kind=note.kind,
                    content=note.text,
                    file_path=note.path,
                    line_start=note.start_line,
                    line_end=note.end_line,
                    replacement=note.replacement,
                    base_hash=base_hash,
                )
                saved = await service.add_note(
                    ide_session_id, data, error_key=error_key, level=note.level
                )
            except ValidationError:
                logger.info("Professor note refused: session %s, invalid fields", ide_session_id)
                return None
            except AppError as exc:
                if exc.code not in STALE_CODES:
                    raise
                logger.info("Professor note stale: session %s, %s", ide_session_id, exc.code)
                await db.rollback()
                return None
            await db.commit()
            return saved.id

    async def verify(self, user_id: str, draft: ExerciseDraft) -> Verification:
        """The exercise's tests on its solution, in the sandbox (never here). The exercise's test
        files are put back over the solution: it cannot change them. Refused files or names
        count as a readable failure."""
        try:
            ExerciseIn(
                title=draft.title,
                statement=draft.statement,
                files=draft.files,
                entry=draft.entry,
            )
        except ValidationError:
            return Verification(False, "refused", "The exercise files are refused.")
        tests = {name: text for name, text in draft.files.items() if _is_test(name)}
        job = SandboxJob(
            run_id=uuid4().hex,
            files={**draft.solution, **tests},
            entry=draft.entry,
            kind="check",
            timeout_s=VERIFY_TIMEOUT_S,
        )
        sandbox = self._providers.sandbox
        if sandbox is None:
            raise AppError("sandbox_unavailable", "The code sandbox is unavailable.", 503)
        try:
            await sandbox.submit(job)
        except ValueError:
            return Verification(False, "refused", "The solution exceeds the sandbox limits.")
        except OSError:
            raise AppError("sandbox_unavailable", "The code sandbox is unavailable.", 503) from None
        return await _result(sandbox, job.run_id)

    async def save_exercise(
        self, user_id: str, agent_session_id: str, draft: ExerciseDraft, topic: str
    ) -> str:
        """Stores the verified exercise (origin `generated`); the solution is never stored."""
        async with self._factory() as db:
            data = ExerciseIn(
                title=draft.title,
                statement=draft.statement,
                files=draft.files,
                entry=draft.entry,
            )
            saved = await IdeService(db, user_id, None, PROFESSOR).create_exercise(
                data, origin="generated", topic=topic, agent_session_id=agent_session_id
            )
            await db.commit()
            return saved.id


def _is_test(name: str) -> bool:
    return name.rsplit("/", 1)[-1].startswith("test_")


async def _result(box: CodeSandbox, run_id: str) -> Verification:
    """Polls the sandbox until the job is done (at most `VERIFY_WAIT_S`)."""
    started = monotonic()
    while True:
        try:
            progress = await box.poll(run_id, 0)
        except UnknownRun:
            return Verification(False, "error", "The sandbox returned no result.")
        except OSError:
            raise AppError("sandbox_unavailable", "The code sandbox is unavailable.", 503) from None
        if progress.result is not None:
            ok = progress.result.status == "done" and progress.result.exit_code == 0
            return Verification(ok, progress.result.status, progress.output)
        if monotonic() - started > VERIFY_WAIT_S:
            await box.cancel(run_id)
            return Verification(False, "timeout", progress.output)
        await asyncio.sleep(POLL_S)
