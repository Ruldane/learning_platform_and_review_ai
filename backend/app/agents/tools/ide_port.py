"""Port of the Python IDE (phase 10, 10.A3). `app.agents` imports no feature (contract 6): it
describes here what the `ide_teacher` and `ide_exercise` graphs need; the `ide` feature
implements it (`AgentIdeStore`).

January's code, the output of her runs and the statement of an exercise are data: never
logged. Writes go through the same service as Claude's (`IdeService`), under the internal
caller "professor": same validations, same notes.

- `teacher_inputs`: read-only (session, last run, notes, style).
- `save_note`: stores the teacher's note; `None` if the code changed in the meantime (the
  proposal is stale, or the range no longer exists): nothing is stored.
- `verify`: runs an exercise's tests in the sandbox (never here, never in-process);
  `save_exercise` stores the verified exercise."""

from dataclasses import dataclass, field
from typing import Literal, Protocol

from app.agents.tools.ide_schema import ExerciseDraft, TeacherNote
from app.core.errors import AppError

Style = Literal["guide", "pair"]


@dataclass(frozen=True)
class RunView:
    """The last run: full output (64 KiB at most), signature of its error."""

    id: str
    kind: str
    status: str
    exit_code: int | None
    output: str
    error_signature: str | None


@dataclass(frozen=True)
class NoteView:
    id: str
    kind: str
    author: str
    level: int | None
    file_path: str | None
    line_start: int | None
    text: str
    error_key: str | None


@dataclass(frozen=True)
class TeachInputs:
    title: str
    statement: str | None  # the exercise statement (`None`: free session)
    files: dict[str, str]
    entry: str
    passed: bool
    style: Style
    run: RunView | None
    notes: list[NoteView] = field(default_factory=list)  # the oldest first


@dataclass(frozen=True)
class Verification:
    """The sandbox's answer to a check: `passed` if the tests pass (code 0)."""

    passed: bool
    status: str
    output: str


class IdeStore(Protocol):
    async def teacher_inputs(
        self, user_id: str, ide_session_id: str, run_id: str | None
    ) -> TeachInputs: ...

    async def save_note(
        self,
        user_id: str,
        ide_session_id: str,
        note: TeacherNote,
        *,
        base_hash: str | None,
        error_key: str | None,
    ) -> str | None: ...

    async def verify(self, user_id: str, draft: ExerciseDraft) -> Verification: ...

    async def save_exercise(
        self, user_id: str, agent_session_id: str, draft: ExerciseDraft, topic: str
    ) -> str: ...


def ide_unavailable() -> AppError:
    return AppError("ide_unavailable", "The IDE is unavailable in this runtime.", 503)


class _NoIde:
    """Engine default value (tests, starts without the feature)."""

    async def teacher_inputs(
        self, user_id: str, ide_session_id: str, run_id: str | None
    ) -> TeachInputs:
        raise ide_unavailable()

    async def save_note(
        self,
        user_id: str,
        ide_session_id: str,
        note: TeacherNote,
        *,
        base_hash: str | None,
        error_key: str | None,
    ) -> str | None:
        raise ide_unavailable()

    async def verify(self, user_id: str, draft: ExerciseDraft) -> Verification:
        raise ide_unavailable()

    async def save_exercise(
        self, user_id: str, agent_session_id: str, draft: ExerciseDraft, topic: str
    ) -> str:
        raise ide_unavailable()


NO_IDE: IdeStore = _NoIde()
