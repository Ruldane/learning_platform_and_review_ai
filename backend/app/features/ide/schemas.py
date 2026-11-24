"""Python IDE schemas (phase 10, P1): final as of 10.P; a flow never changes the surface (if it
must, it regenerates `contracts/openapi.json` and `schema.d.ts` and says so)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

from app.db.models.ide import (
    ExerciseOrigin,
    NoteAuthor,
    NoteKind,
    NoteStatus,
    Origin,
    RunKind,
    RunStatus,
    TeacherMode,
    TeacherStyle,
)
from app.features.ide.hashing import file_hash, is_file_hash
from app.features.ide.schemas_exercise import (
    PATH_MAX,
    TITLE_MAX,
    ExerciseGenerateIn,
    ExerciseIn,
    ExerciseOut,
    ExercisePatch,
    check_files,
)
from app.features.ide.schemas_project import ProjectTabsState

__all__ = [
    "ExerciseGenerateIn",
    "ExerciseIn",
    "ExerciseOrigin",
    "ExerciseOut",
    "ExercisePatch",
    "FilesPutIn",
    "NoteAuthor",
    "NoteIn",
    "NoteKind",
    "NoteOut",
    "NoteStatus",
    "Origin",
    "PreferencesIn",
    "PreferencesOut",
    "RunIn",
    "RunKind",
    "RunOut",
    "RunProgress",
    "RunStatus",
    "SessionCreateIn",
    "IdeSessionOut",
    "IdeSessionStarted",
    "SessionSummary",
    "TeachIn",
    "TeachOut",
    "TeacherMode",
    "TeacherStyle",
    "UsageOut",
]

NOTE_MAX = 4_000
QUESTION_MAX = 2_000

TeachTrigger = Literal["run_error", "run_ok", "question", "hint", "idle"]
SkipReason = Literal["cap_reached", "on_demand", "busy"]


class IdeSessionStarted(BaseModel):
    """The graph is running: `session_id` is the agent session to follow (within 2 s)."""

    session_id: str


class SessionCreateIn(BaseModel):
    """Opens a session on an exercise, or a free session (without `exercise_id`)."""

    exercise_id: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=TITLE_MAX)


class SessionSummary(BaseModel):
    """`passed`: the session had a successful check (`check`) (`passed_at`: the first one)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    exercise_id: str | None
    updated_at: datetime
    passed: bool
    passed_at: datetime | None


class IdeSessionOut(SessionSummary):
    exercise_statement: str | None = None
    """`file_hashes`: the sha256 of each file (the `base_hash` Claude sends back)."""

    files: dict[str, str]
    entry: str
    files_version: int = 0
    tabs: ProjectTabsState | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def file_hashes(self) -> dict[str, str]:
        return {name: file_hash(text) for name, text in self.files.items()}


class FilesPutIn(BaseModel):
    """Saves the session's files. Interface: replaces all files. Claude (MCP, switch on): a single
    file in `files`, the others are kept; `base_hash` is then required: the sha256 of that file's
    current content (the session's `file_hashes`; empty text for a new file). It is ignored for
    the interface. So is `entry`, for Claude. `base_hashes` (interface, optional): the sha256 of
    the version of each file you edited from; a file Claude has changed since, which the upload
    would overwrite, gives 409 `stale_base` (`details.files`: the names) and nothing is
    written."""

    files: dict[str, str]
    entry: str | None = Field(default=None, min_length=1, max_length=PATH_MAX)
    base_hash: str | None = Field(default=None, min_length=64, max_length=64)
    base_hashes: dict[str, str] | None = None

    _files = field_validator("files")(check_files)

    @field_validator("base_hashes")
    @classmethod
    def _hashes(cls, hashes: dict[str, str] | None) -> dict[str, str] | None:
        if hashes is not None and not all(is_file_hash(value) for value in hashes.values()):
            raise ValueError("invalid hash")
        return hashes


class RunIn(BaseModel):
    """`run` executes `entry`; `check` runs the exercise's tests with pytest in the sandbox (exit
    code 0 = passed). `entry`: the entry file (the session's by default)."""

    kind: RunKind = "run"
    entry: str | None = Field(default=None, min_length=1, max_length=PATH_MAX)


class RunOut(BaseModel):
    """A submitted run (202): the output is read through `GET /ide/runs/{id}?after=`. `origin`:
    `mcp` when Claude started it (the page shows "started by Claude")."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    kind: RunKind
    entry: str
    status: RunStatus
    created_at: datetime
    origin: Origin


class RunProgress(BaseModel):
    """The output since `after` (bytes), the next offset, and the end once the
    sandbox returned it."""

    id: str
    status: RunStatus
    output: str
    next_offset: int
    exit_code: int | None
    duration_ms: int | None
    truncated: bool


class TeachIn(BaseModel):
    """What triggers the professor: a failed (`run_error`) or successful (`run_ok`) run, a question
    (`question`, non-empty: 422 otherwise), a hint request (`hint`) or, optionally, 30 s stopped
    on a line (`idle`). Never on typing."""

    trigger: TeachTrigger
    question: str | None = Field(default=None, max_length=QUESTION_MAX)
    file_path: str | None = Field(default=None, max_length=PATH_MAX)
    line: int | None = Field(default=None, ge=1)
    run_id: str | None = None

    @model_validator(mode="after")
    def _question_needed(self) -> "TeachIn":
        if self.trigger == "question" and not (self.question or "").strip():
            raise ValueError("the question is empty")
        return self


class TeachOut(BaseModel):
    """Only one of the three: `session_id` (the professor's graph is working), `reference_note_id`
    (same error at the same place: pointer to the previous note) or `skipped` (why nothing is
    started)."""

    session_id: str | None = None
    reference_note_id: str | None = None
    skipped: SkipReason | None = None


class NoteIn(BaseModel):
    """A note added by hand or by Claude: the author comes from the caller, never from the body.
    A proposal carries `replacement`, the line range and `base_hash`: the hexadecimal sha256
    (lowercase, 64 characters) of the file's content encoded in UTF-8."""

    kind: NoteKind
    content: str = Field(min_length=1, max_length=NOTE_MAX)
    file_path: str | None = Field(default=None, max_length=PATH_MAX)
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)
    replacement: str | None = Field(default=None, max_length=NOTE_MAX)
    base_hash: str | None = Field(default=None, min_length=64, max_length=64)


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    kind: NoteKind
    author: NoteAuthor
    author_label: str | None
    origin: Origin  # `mcp`: written by Claude (the page shows "Claude")
    status: NoteStatus
    file_path: str | None
    line_start: int | None
    line_end: int | None
    content: str
    replacement: str | None
    base_hash: str | None
    reference_note_id: str | None
    level: int | None  # actual level of a graded hint (1 to 3), empty for other notes
    created_at: datetime


class PreferencesIn(BaseModel):
    """Professor mode (`auto` or on demand), style (`guide`: graded hints; `pair`: pair
    programming, margin annotations and proposals to accept), idle timer (30 s, optional), token
    caps, and the "Claude can write to my files" switch (`mcp_can_write_files`, off by default:
    only the interface sets it, never MCP)."""

    teacher_mode: TeacherMode = "auto"
    teacher_style: TeacherStyle = "guide"
    idle_trigger: bool = False
    mcp_can_write_files: bool = False
    session_cap: int = Field(default=100_000, ge=1_000, le=2_000_000)
    day_cap: int = Field(default=300_000, ge=1_000, le=10_000_000)


class PreferencesOut(PreferencesIn):
    model_config = ConfigDict(from_attributes=True)


class UsageOut(BaseModel):
    """The professor's usage: session and day tokens, their caps, and whether the professor
    switched to "on demand" mode (cap reached or by choice)."""

    session_tokens: int
    day_tokens: int
    session_cap: int
    day_cap: int
    mode_on_demand: bool
