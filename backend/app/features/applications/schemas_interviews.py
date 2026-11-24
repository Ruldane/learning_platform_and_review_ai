"""Mock interview schemas (SPEC F10, D146). A 422 names the fields (`details.fields`), never
their value: the job title, the answers and the debrief are personal data.

`status`: `running` (in progress), `done` (debrief written), `stopped` (stopped before any
answer), `debrief_failed` (the answers are kept, the debrief could not be written: no scores, no
cards), `failed` (the session ended without a result)."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, StringConstraints

from app.agents.tools.interview_schema import Criterion, QuestionSource, ScoreKey
from app.agents.tools.negotiation import SalaryOutcome, SalarySample
from app.db.models.applications import InterviewMode as InterviewMode
from app.db.models.applications import InterviewStatus as InterviewStatus
from app.features.applications.schemas import Id

ROLE_MAX = 200
Role = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=ROLE_MAX)]
RadarLabel = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class InterviewIn(BaseModel):
    """An interview's settings: the format (behavioral, technical, case study, mixed), the
    length (4, 7 or 10 main questions) and the language of the questions."""

    mode: InterviewMode
    duration_min: Literal[15, 30, 45]
    language: Literal["fr", "en"] = "fr"
    radar_role: RadarLabel | None = None
    radar_zone: RadarLabel | None = None


class FreeInterviewIn(InterviewIn):
    """An interview without a record: on a posting (`posting_id`) or a job title only (`role`).
    One or the other, not both nor neither (422 `fields: ["posting_id", "role"]`)."""

    posting_id: Id | None = None
    role: Role | None = None
    system_design: Literal[True] | None = None


class InterviewStartOut(BaseModel):
    interview_id: str
    session_id: str


class ExchangeOut(BaseModel):
    """A main question, January's answer, the follow-up question and its answer if any, the
    internal score (1 to 5); `unrated`: the model did not answer, the score is neutral."""

    index: int
    question: str
    criterion: Criterion
    source: QuestionSource
    answer: str
    follow_up: str | None
    follow_up_answer: str | None
    note: int
    unrated: bool


class ExpectedOut(BaseModel):
    """The points a good answer to question `index` would have given (back of the card)."""

    index: int
    points: list[str]


class DebriefOut(BaseModel):
    """The debrief: four scores (1 to 5), three strengths, three fixes, the improved answer to
    question `weakest_index` (to check if `flags` is not empty), the missed questions (`missed`,
    internal score 2 at most) and their expected points, the unrated answers (`unrated`)."""

    scores: dict[ScoreKey, int]
    strengths: list[str]
    fixes: list[str]
    weakest_index: int
    improved_answer: str
    missed: list[int]
    expected: list[ExpectedOut]
    unrated: list[int]


class InterviewOut(BaseModel):
    """An interview. `flags`: the terms in the improved answer that the profile does not state.
    `cards_created`: the new revision cards (one per missed question, due tomorrow)."""

    id: str
    application_id: str | None
    posting_id: str | None
    role: str | None
    mode: InterviewMode
    duration_min: Literal[15, 30, 45]
    language: Literal["fr", "en"]
    session_id: str
    status: InterviewStatus
    exchanges: list[ExchangeOut]
    debrief: DebriefOut | None
    flags: list[str]
    cards_created: int
    created_at: datetime
    salary: SalarySample | None = None
    salary_outcome: SalaryOutcome | None = None
