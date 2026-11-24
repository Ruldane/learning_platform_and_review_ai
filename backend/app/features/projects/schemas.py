"""Mini project contract (SPEC 14.2, P1 to P3, P19, D166). A 422 names the fields, never their
value (description, repository link, draft text: personal data, 17.2)."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, model_validator

from app.db.models.daily import DraftKind, DraftStatus, ProjectStatus

__all__ = [
    "CriterionOut",
    "DraftKind",
    "DraftOut",
    "DraftPatchIn",
    "DraftStatus",
    "EvaluationOut",
    "ProfileEntryIn",
    "ProjectBriefOut",
    "ProjectOut",
    "ProjectStatus",
    "ProjectSummary",
    "SessionStarted",
    "SubmissionOut",
]

CONTENT_MAX = 3_000
# Project entry texts are stripped before being measured: a blank name or achievement
# is a 422, never a profile error (D166).
_STRIP = {"strip_whitespace": True}
EntryName = Annotated[str, StringConstraints(**_STRIP, min_length=1, max_length=120)]
EntryLine = Annotated[str, StringConstraints(**_STRIP, min_length=1, max_length=200)]
EntryText = Annotated[str, StringConstraints(**_STRIP, max_length=600)]


class ProjectBriefOut(BaseModel):
    """The brief written by the Practitioner."""

    title: str
    context: str
    objective: str
    constraints: list[str]
    criteria: list[str]
    hours: int
    deliverable: Literal["repo", "description", "either"]


class SubmissionOut(BaseModel):
    """A submission. `screenshots`: the number of screenshots
    (`GET /projects/{id}/screenshots/{n}`)."""

    at: datetime
    repo_url: str | None
    description: str | None
    screenshots: int


class CriterionOut(BaseModel):
    index: int
    criterion: str
    met: bool
    comment: str


class EvaluationOut(BaseModel):
    """The latest review: the verdict is the code's. `repo_status`: could the repository be
    read? (`none`: no link given)."""

    at: datetime | None
    verdict: Literal["validated", "to_redo"]
    results: list[CriterionOut]
    feedback: str
    repo_status: Literal["read", "unreadable", "none"]


class ProfileEntryIn(BaseModel):
    """The master profile project entry: January's text, possibly edited."""

    name: EntryName
    description: EntryText = ""
    achievements: list[EntryLine] = Field(default_factory=list, max_length=4)


class DraftOut(BaseModel):
    """A draft in January's name. `to_check`: `flags` names what her profile and project do not
    say (or the length). `edited`: January edited it."""

    kind: DraftKind
    status: DraftStatus
    content: str
    entry: ProfileEntryIn | None
    flags: list[str]
    edited: bool


class ProjectOut(BaseModel):
    id: str
    module_id: str
    program_id: str
    title: str
    status: ProjectStatus
    brief: ProjectBriefOut | None
    submissions: list[SubmissionOut]
    evaluation: EvaluationOut | None
    drafts: list[DraftOut]
    validated_at: datetime | None
    profile_version: int | None
    session_id: str | None


class ProjectSummary(BaseModel):
    """A Portfolio row. `week` (from 1) and `rank` (within the week, like `GET
    /programs`): the module's place in its program (`None` if the module no longer exists)."""

    id: str
    module_id: str
    program_id: str
    program_title: str | None
    title: str
    status: ProjectStatus
    week: int | None
    rank: int | None
    hours: int | None
    skills: list[str]
    validated_at: datetime | None
    profile_version: int | None
    session_id: str | None


class SessionStarted(BaseModel):
    session_id: str


class DraftPatchIn(BaseModel):
    """An edited draft: `entry` for the project entry, `content` for the other three.
    Only one of the two, depending on the kind."""

    content: str | None = Field(default=None, min_length=1, max_length=CONTENT_MAX)
    entry: ProfileEntryIn | None = None


class ProjectBriefIn(BaseModel):
    """A mini project brief written by hand or by Claude (no agent): same bounds as the
    Practitioner's (`ProjectBrief`): 2 to 5 constraints, 3 to 6 checkable criteria, 3 to 6
    hours."""

    title: str = Field(min_length=3, max_length=120)
    context: str = Field(min_length=1, max_length=900)
    objective: str = Field(min_length=1, max_length=450)
    constraints: list[Annotated[str, Field(min_length=1, max_length=160)]] = Field(
        min_length=2, max_length=5
    )
    criteria: list[Annotated[str, Field(min_length=1, max_length=200)]] = Field(
        min_length=3, max_length=6
    )
    hours: int = Field(ge=3, le=6)
    deliverable: Literal["repo", "description", "either"]


class ProjectCreateIn(BaseModel):
    """A module's mini project (one per module): its brief, ready to submit."""

    module_id: str = Field(min_length=1, max_length=36)
    brief: ProjectBriefIn


class ProjectBriefPatch(BaseModel):
    """Brief edit: the given fields replace the brief's, the others stay."""

    title: str | None = Field(default=None, min_length=3, max_length=120)
    context: str | None = Field(default=None, min_length=1, max_length=900)
    objective: str | None = Field(default=None, min_length=1, max_length=450)
    constraints: list[Annotated[str, Field(min_length=1, max_length=160)]] | None = Field(
        default=None, min_length=2, max_length=5
    )
    criteria: list[Annotated[str, Field(min_length=1, max_length=200)]] | None = Field(
        default=None, min_length=3, max_length=6
    )
    hours: int | None = Field(default=None, ge=3, le=6)
    deliverable: Literal["repo", "description", "either"] | None = None

    @model_validator(mode="after")
    def _something(self) -> "ProjectBriefPatch":
        if not self.model_dump(exclude_none=True):
            raise ValueError("nothing to change")
        return self
