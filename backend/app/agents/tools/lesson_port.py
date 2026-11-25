"""Port for lessons (D90). `app.agents` imports no feature (contract 6): it describes here what
the `lesson_factory` graph needs (the module record, the publication of the lesson and its
resources, the failure, the next module); the `lessons` feature will implement it (task 4.10).

Each write is idempotent per module: a node replayed after a stop (SPEC 9.4) rewrites the
same thing, never one more lesson or resource.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol

from pydantic import BaseModel, Field, field_validator

from app.agents.runtime.prose import Prose
from app.core.errors import AppError
from app.db.models.lessons import ResourceLevel, ResourceType

MAX_SEED_URLS = 5
_LEGACY_TYPES = {"cours": "course", "depot": "repository", "papier": "paper"}
_LEGACY_LEVELS = {"debutant": "beginner", "intermediaire": "intermediate", "avance": "advanced"}


@dataclass(frozen=True)
class ModuleBrief:
    """The module whose lesson is written, as the program set it."""

    module_id: str
    program_id: str
    title: str
    skills: tuple[str, ...]
    prerequisites: tuple[str, ...]
    week_rank: int
    week_theme: str
    goal_text: str  # January's goal, to place the lesson
    language: str  # lesson language (`lesson_language` setting)
    # Practitioners' pages and the Council's kept sources linked to the module (5 at most).
    seed_urls: tuple[str, ...]
    chapter_context: str = ""
    # Deprecated or now secondary APIs of the chapter: to show only in the box
    # "Reading old code", never as the recommended way.
    legacy: tuple[str, ...] = ()


class ResourcePick(BaseModel):
    """A resource kept for the module (SPEC 3.6): a source rated 60 or more in the
    session. Author, date and language are read by the port from the source, never by the model."""

    source_id: str
    type: ResourceType
    duration_minutes: int = Field(ge=1, le=600)
    level: ResourceLevel
    reason: Prose = Field(min_length=5, max_length=200)

    @field_validator("type", mode="before")
    @classmethod
    def read_checkpoint_type(cls, value: object) -> object:
        return _LEGACY_TYPES.get(value, value) if isinstance(value, str) else value

    @field_validator("level", mode="before")
    @classmethod
    def read_checkpoint_level(cls, value: object) -> object:
        return _LEGACY_LEVELS.get(value, value) if isinstance(value, str) else value


class ResourcePicks(BaseModel):
    resources: list[ResourcePick] = Field(min_length=3, max_length=6)


@dataclass(frozen=True)
class LessonReport:
    """Verifier's report stored with the lesson. On publication `unsupported` is empty and
    `problems` only keeps minor remarks (for example resources in insufficient
    number)."""

    words: int
    unsupported: tuple[str, ...]
    problems: tuple[str, ...]
    revisions: int
    scores: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class LessonSubmission:
    title: str
    markdown: str
    urls: tuple[str, ...]


@dataclass(frozen=True)
class PublishedLesson:
    lesson_id: str
    pdf_ok: bool  # the PDF could be produced; otherwise the lesson can still be read in the app
    resources: int


class LessonStore(Protocol):
    async def brief(self, user_id: str, module_id: str) -> ModuleBrief:
        """The user's module record; `module_not_found` (404) if it is not theirs."""
        ...

    async def submission(self, user_id: str, session_id: str, module_id: str) -> LessonSubmission:
        """Reads the private draft allowed for the verification session."""
        ...

    async def publish(
        self,
        user_id: str,
        session_id: str,
        module_id: str,
        *,
        markdown: str,
        resources: Sequence[ResourcePick],
        report: LessonReport,
        verification: bool = False,
    ) -> PublishedLesson:
        """Stores the ready lesson, its resources and its PDF; idempotent per module: replayed, it
        returns the same lesson without writing one more row."""
        ...

    async def fail(
        self,
        user_id: str,
        session_id: str,
        module_id: str,
        reason: str,
        *,
        verification: bool = False,
        feedback: Sequence[str] = (),
    ) -> None:
        """Marks the module's lesson as failed, with a readable reason; idempotent. For a
        submission (`verification`), `feedback` keeps the detailed remarks of the check."""
        ...

    async def next_module(
        self, user_id: str, program_id: str, *, exclude_session_id: str
    ) -> str | None:
        """Chains on: starts the lesson of the next due module of the program and returns its
        id, or `None` if none is left. `exclude_session_id`: the current session, which does not
        count as an already open chain. Idempotent (one chain per program)."""
        ...


def lessons_unavailable() -> AppError:
    return AppError("lessons_unavailable", "Lessons are unavailable in this runtime.", 503)


class _NoLessons:
    """Engine default value (existing tests, starts without the `lessons` feature)."""

    async def brief(self, user_id: str, module_id: str) -> ModuleBrief:
        raise lessons_unavailable()

    async def submission(self, user_id: str, session_id: str, module_id: str) -> LessonSubmission:
        raise lessons_unavailable()

    async def publish(
        self,
        user_id: str,
        session_id: str,
        module_id: str,
        *,
        markdown: str,
        resources: Sequence[ResourcePick],
        report: LessonReport,
        verification: bool = False,
    ) -> PublishedLesson:
        raise lessons_unavailable()

    async def fail(
        self,
        user_id: str,
        session_id: str,
        module_id: str,
        reason: str,
        *,
        verification: bool = False,
        feedback: Sequence[str] = (),
    ) -> None:
        raise lessons_unavailable()

    async def next_module(
        self, user_id: str, program_id: str, *, exclude_session_id: str
    ) -> str | None:
        raise lessons_unavailable()


NO_LESSONS: LessonStore = _NoLessons()
