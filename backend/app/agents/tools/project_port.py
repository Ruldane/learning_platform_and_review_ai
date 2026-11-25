"""Port for proof projects (P1 to P4, D165). `app.agents` imports no feature (contract 6): it
describes here what the `project_brief` and `project_review` graphs need; the
`projects` feature implements it (task 8.10).

The brief, January's description, the repository, the criteria and the drafts are data from
the user or the web (17.2, 17.4): never logged, neither here nor by the implementation. Every
write is **idempotent per session** (SPEC 9.4): a node replayed after a stop stores nothing
more (the session's first write wins).

- `brief_inputs` / `review_inputs`: read-only, the project's state as it is in the database.
- `save_brief`: stores the brief; the project moves to "to do".
- `brief_failed`: the brief failed with this code (`structured_output_invalid`...), nothing else;
  "Retry" restarts the graph.
- `repo_text`: the text of **one** repository page (README), `None` if it cannot be read. Hook point
  of phase 14 (GitHub); the graph never reads the web otherwise.
- `save_review`: stores the evaluation. If validated, the port sets the module's skills to `prouve`
  (proof `project`), stores the drafts and writes to the journal; the project entry enters the
  master profile only through January's click (P3).
- `save_drafts`: stores the drafts of an **already validated** project that has none (`drafts` mode
  of `project_review`, D181); no effect if the project is not validated, if it already has
  drafts or if the list is empty."""

from dataclasses import dataclass
from typing import Literal, Protocol

from app.agents.tools.cv_schema import MasterProfileData
from app.agents.tools.project_schema import (
    CriterionResult,
    DraftKind,
    DraftStatus,
    ProfileEntryDraft,
    ProjectBrief,
)
from app.core.errors import AppError

__all__ = [
    "NO_PROJECTS",
    "BriefInputs",
    "DraftResult",
    "ProjectStore",
    "ReviewInputs",
    "ReviewOutcome",
]

LESSON_EXCERPT_MAX = 3_000  # characters of the lesson excerpt shown to the Practitioner


@dataclass(frozen=True)
class BriefInputs:
    """What the Practitioner reads to write the module's brief."""

    module_title: str
    skills: list[str]
    prerequisites: list[str]
    lesson_excerpt: str | None  # 3,000 characters at most
    week_deliverable: str | None  # the module week's deliverable
    role: str | None  # the targeted role
    language: Literal["fr", "en"]


@dataclass(frozen=True)
class ReviewInputs:
    """What the Practitioner reads to assess the submission: the brief and January's work."""

    title: str
    brief: ProjectBrief
    repo_url: str | None
    description: str | None
    screenshots: int  # number of screenshots: never sent to the model (P2)
    skills: list[str]  # the module's skills
    profile: MasterProfileData | None  # the validated master profile
    language: Literal["fr", "en"]


@dataclass(frozen=True)
class DraftResult:
    kind: DraftKind
    content: str  # the checked text (`draft_text`)
    entry: ProfileEntryDraft | None  # only for `profile_entry`
    status: DraftStatus  # `to_check`: terms January did not state, or a length out of bounds
    flags: list[str]  # these terms (or the length), never empty if `to_check`


@dataclass(frozen=True)
class ReviewOutcome:
    verdict: Literal["validated", "to_redo"]
    results: list[CriterionResult]  # one per criterion, in order (`settled_results`)
    feedback: str
    repo_status: Literal["read", "unreadable", "none"]
    drafts: list[DraftResult] | None  # four drafts if validated, otherwise `None`


class ProjectStore(Protocol):
    async def brief_inputs(self, user_id: str, project_id: str) -> BriefInputs: ...

    async def save_brief(
        self, user_id: str, session_id: str, project_id: str, brief: ProjectBrief
    ) -> None: ...

    async def brief_failed(
        self, user_id: str, session_id: str, project_id: str, code: str
    ) -> None: ...

    async def review_inputs(self, user_id: str, project_id: str) -> ReviewInputs: ...

    async def repo_text(self, user_id: str, session_id: str, url: str) -> str | None: ...

    async def save_review(
        self, user_id: str, session_id: str, project_id: str, outcome: ReviewOutcome
    ) -> None: ...

    async def save_drafts(
        self, user_id: str, session_id: str, project_id: str, drafts: list[DraftResult]
    ) -> bool: ...


def projects_unavailable() -> AppError:
    return AppError("projects_unavailable", "Projects are unavailable in this runtime.", 503)


class _NoProjects:
    """Engine default value (tests, starts without the feature)."""

    async def brief_inputs(self, user_id: str, project_id: str) -> BriefInputs:
        raise projects_unavailable()

    async def save_brief(
        self, user_id: str, session_id: str, project_id: str, brief: ProjectBrief
    ) -> None:
        raise projects_unavailable()

    async def brief_failed(self, user_id: str, session_id: str, project_id: str, code: str) -> None:
        raise projects_unavailable()

    async def review_inputs(self, user_id: str, project_id: str) -> ReviewInputs:
        raise projects_unavailable()

    async def repo_text(self, user_id: str, session_id: str, url: str) -> str | None:
        raise projects_unavailable()

    async def save_review(
        self, user_id: str, session_id: str, project_id: str, outcome: ReviewOutcome
    ) -> None:
        raise projects_unavailable()

    async def save_drafts(
        self, user_id: str, session_id: str, project_id: str, drafts: list[DraftResult]
    ) -> bool:
        raise projects_unavailable()


NO_PROJECTS: ProjectStore = _NoProjects()
