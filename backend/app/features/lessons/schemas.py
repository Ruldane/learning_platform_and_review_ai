"""Schemas of the lessons and resources API (SPEC 3.5, 3.6, 14.2; D91)."""

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from app.db.models.lessons import (
    MAX_LESSON_ATTEMPTS,
    LessonStatus,
    ResourceLevel,
    ResourceStatus,
    ResourceType,
)

# The literal types are re-exported: a router does not import `app.db` (contract 1b).
__all__ = [
    "LessonOut",
    "LessonPatch",
    "LessonStatus",
    "LessonSummaryOut",
    "ResourceLevel",
    "ResourceOut",
    "ResourcePatch",
    "ResourceStatus",
    "ResourceType",
    "LessonWriteIn",
]

TITLE_MAX = 200
MARKDOWN_MIN = 300  # an agent lesson passes the Verifier (1,200 words); this is a floor
MARKDOWN_MAX = 60_000
RESOURCES_MAX = 12


class ResourceOut(BaseModel):
    """A module resource: link, source metadata (author, date, language) and the reason it was
    chosen; `has_local_copy`: free PDF kept on disk (`GET /resources/{id}/file`), otherwise
    `note` is the reading note."""

    id: str
    module_id: str
    program_id: str
    type: ResourceType
    title: str
    url: str
    author: str | None
    date: str | None = Field(description="Publication date as given by the source.")
    lang: str | None
    duration_minutes: int | None
    level: ResourceLevel | None
    reason: str
    score: int | None
    status: ResourceStatus
    has_local_copy: bool
    note: str | None


class LessonSummaryOut(BaseModel):
    id: str
    module_id: str
    week_rank: int
    title: str
    status: LessonStatus = Field(
        description="`pending`: not started yet (weeks 3 and later: 7 days before they "
        "start); `generating`; `ready`; `failed` (retried automatically, 3 attempts in all)."
    )
    attempts: int = Field(
        ge=0,
        le=MAX_LESSON_ATTEMPTS,
        description=f"Production attempts made ({MAX_LESSON_ATTEMPTS} at most): a `failed` "
        f"lesson with fewer than {MAX_LESSON_ATTEMPTS} attempts will be retried.",
    )
    word_count: int
    pdf_available: bool
    done_tasks: int = Field(ge=0, description="Done tasks of the lesson's module (program).")
    total_tasks: int = Field(ge=0, description="Tasks of the lesson's module.")
    completed: bool = Field(
        description="All of the module's tasks are done (at least one): lesson completed."
    )
    verification_session_id: str | None = Field(
        default=None, description="Verification session of a direct write in progress."
    )
    verification_failure_reason: str | None = Field(
        default=None, description="Reason for the last failed verification of a direct write."
    )


class LessonOut(LessonSummaryOut):
    program_id: str
    markdown: str
    failure_reason: str | None
    resources: list[ResourceOut]
    verification_feedback: list[str] = Field(
        default_factory=list,
        description="Remarks from the last rejected check of a direct write: reasoned scores "
        "below the minimum and unsourced claims (D308). Empty otherwise.",
    )


class ResourcePatch(BaseModel):
    status: ResourceStatus


class ResourceWriteIn(BaseModel):
    """A reading link provided with a lesson, saved without downloading the page."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    url: HttpUrl
    title: str = Field(min_length=1, max_length=TITLE_MAX)
    type: ResourceType
    reason: str = Field(min_length=1, max_length=300)
    author: str | None = Field(default=None, min_length=1, max_length=200)
    date: str | None = Field(default=None, min_length=1, max_length=32)
    lang: str | None = Field(default=None, min_length=1, max_length=8)
    duration_minutes: int | None = Field(default=None, ge=1, le=600)
    level: ResourceLevel | None = None

    @field_validator("url")
    @classmethod
    def _no_credentials(cls, url: HttpUrl) -> HttpUrl:
        if url.username is not None or url.password is not None:
            raise ValueError("The link must not contain credentials.")
        return url


class LessonWriteIn(BaseModel):
    """A module's draft submitted to the Factory. By default, the module title is used."""

    title: str | None = Field(default=None, min_length=1, max_length=TITLE_MAX)
    markdown: str = Field(min_length=MARKDOWN_MIN, max_length=MARKDOWN_MAX)
    resources: list[ResourceWriteIn] = Field(default_factory=list, max_length=RESOURCES_MAX)


class LessonPatch(BaseModel):
    """Edit of a ready lesson's title or text, or addition of resources."""

    title: str | None = Field(default=None, min_length=1, max_length=TITLE_MAX)
    markdown: str | None = Field(default=None, min_length=MARKDOWN_MIN, max_length=MARKDOWN_MAX)
    resources: list[ResourceWriteIn] = Field(default_factory=list, max_length=RESOURCES_MAX)

    @model_validator(mode="after")
    def _something(self) -> "LessonPatch":
        if self.title is None and self.markdown is None and not self.resources:
            raise ValueError("nothing to change")
        return self
