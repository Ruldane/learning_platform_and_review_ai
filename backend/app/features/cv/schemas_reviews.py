"""Schemas of CV reviews, their modifications and the versions produced (SPEC 5.3, 14.2;
D130). The texts of a modification (`before`, `after`) are from January's CV: returned to her
only, never logged; a 422 names the fields (`details.fields`), never their value."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.agents.tools.cv_indicators import AtsCheckId
from app.agents.tools.cv_review_port import ReviewReport
from app.agents.tools.cv_schema import ModificationAction, ModificationType, SectionKey
from app.db.models.career import ModificationStatus, ReviewStatus, VersionStatus

Decision = Literal["accepted", "refused"]


class ErrorDetailOut(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None


class ErrorOut(BaseModel):
    """The envelope of every business error: `{error: {code, message, details}}`."""

    error: ErrorDetailOut


class ReviewStart(BaseModel):
    posting_id: str = Field(min_length=1, max_length=36)


class ReviewStarted(BaseModel):
    """Review started: the review (`running`) and its `cv_review` session (to follow through its
    events)."""

    review_id: str
    session_id: str


class AtsCheckOut(BaseModel):
    """An ATS readability check; `detail`: an English sentence without CV text."""

    id: AtsCheckId
    passed: bool
    detail: str


class IndicatorsOut(BaseModel):
    """Coverage of the posting's mandatory requirements (`missing`: their text, as the posting
    writes it) and ATS checks. No guarantee of passing is promised."""

    coverage_percent: int
    covered: int
    total: int
    missing: list[str]
    checks: list[AtsCheckOut]


class ModificationOut(BaseModel):
    """A proposed modification. `ref`: "a3" (ATS Reader) or "r2" (Recruiter); `before`: the
    targeted text in the original CV (empty for an addition or a move); `after`: the new text
    (for `move`, the key of the section before which `section` goes); `blocks`: why it is
    "to confirm" (fixed sentences); `fact_ids`: the profile facts it rests on; `author`:
    `ats_reader` or `recruiter`."""

    id: str
    ref: str
    section: SectionKey
    action: ModificationAction
    type: ModificationType
    before: str
    after: str
    reason: str
    status: ModificationStatus
    blocks: list[str]
    fact_ids: list[str]
    author: str


class VersionOut(BaseModel):
    """A CV produced for a posting (`number` counts per posting). `indicators`: after rendering
    (coverage of the lines backed by a fact, ATS checks of the rendered PDF), `None` before;
    `filename`: ASCII name of the PDF (`CV_<Name>_<Company>_<Role>.pdf`); `decisions`: the
    decision on each modification at the click (`ref` → `accepted`, `refused`, `proposed`,
    `to_confirm`, or `ignored` for an accepted one the composition could not place);
    `failure_reason`: an English sentence for a rendering failure."""

    id: str
    review_id: str
    posting_id: str
    number: int
    status: VersionStatus
    page_count: int | None
    original_page_count: int
    allow_extra_pages: bool
    filename: str
    decisions: dict[str, str]
    indicators: IndicatorsOut | None
    created_at: datetime
    failure_reason: str | None


class CvReviewOut(BaseModel):
    """`before`: indicators of the original CV; `gap_terms`: posting keywords that the cited
    facts do not carry, to back with a fact or to acquire (they do not enter the CV);
    `waiting_output`: the session is waiting on "What do you want now?" (the only moment when
    "Generate the PDF" is possible)."""

    id: str
    posting_id: str
    status: ReviewStatus
    session_id: str | None
    before: IndicatorsOut | None
    modifications: list[ModificationOut]
    gap_terms: list[str]
    report: ReviewReport | None
    versions: list[VersionOut]
    waiting_output: bool
    created_at: datetime


class ModificationPatch(BaseModel):
    """Decision on a modification. `after`: text rewritten by January (re-validated against the
    profile); `confirm`: "I confirm this is true", the only way to accept a "to confirm"
    modification (the fact then enters the master profile)."""

    status: Decision
    after: str | None = Field(default=None, min_length=1, max_length=600)
    confirm: bool = False

    @field_validator("after")
    @classmethod
    def _not_blank(cls, value: str | None) -> str | None:
        """A text made only of spaces is refused (422 `fields: ["after"]`)."""
        if value is not None and not value.strip():
            raise ValueError("empty text")
        return value


class BulkDecision(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=50)
    status: Decision


class BulkResult(BaseModel):
    """`skipped`: the "to confirm" modifications (never accepted as a group) and the ids
    unknown to the review."""

    updated: int
    skipped: list[str]


class GenerateIn(BaseModel):
    """`allow_extra_pages`: keep a CV longer than the original rather than stop."""

    allow_extra_pages: bool = False


class GenerateStarted(BaseModel):
    version_id: str
