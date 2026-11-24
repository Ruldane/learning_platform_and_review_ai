"""Quiz and review contract (SPEC F9, D101). A question's correct answer, rubric and
explanation only come out with an attempt's grade (`ResultOut`)."""

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import UUID4, BaseModel, Field, model_validator

from app.agents.tools.quiz_port import (
    MAX_CHOICES,
    MAX_QUESTIONS,
    MIN_CHOICES,
    MIN_PROMPT_CHARS,
)
from app.core.practice import MAX_QUIZ_ELAPSED_MS
from app.db.models.study import QuestionType

QuizStatusOut = Literal["generating", "ready", "failed"]
AttemptStatusOut = Literal["grading", "graded", "failed"]


class QuizStarted(BaseModel):
    quiz_id: str
    session_id: str | None
    status: QuizStatusOut


class QuizSummaryOut(BaseModel):
    module_id: str
    module_title: str
    week_rank: int
    quiz_id: str | None
    status: QuizStatusOut | None
    best_score: int | None
    retry_on: date | None


class QuestionOut(BaseModel):
    id: str
    rank: int  # displayed rank (questions shuffled on a retry, F27)
    type: QuestionType
    prompt: str
    code: str | None
    choices: list[str]


class AttemptSummaryOut(BaseModel):
    id: str
    status: AttemptStatusOut
    score: int | None
    created_at: datetime


class QuizOut(BaseModel):
    id: str
    module_id: str
    title: str
    status: QuizStatusOut
    failure_reason: str | None
    session_id: str | None
    questions: list[QuestionOut]
    attempts: list[AttemptSummaryOut]


class AnswerIn(BaseModel):
    question_id: str = Field(min_length=1, max_length=36)
    choice: int | None = None  # rank of the choice as displayed (MCQ only)
    text: str = Field("", max_length=4000)


class AttemptCreate(BaseModel):
    answers: list[AnswerIn] = Field(max_length=50)
    elapsed_ms: int | None = Field(default=None, ge=0, le=MAX_QUIZ_ELAPSED_MS, strict=True)


class AttemptStarted(BaseModel):
    attempt_id: str
    session_id: str


class ResultOut(BaseModel):
    question_id: str
    points: float
    correct_answer: str
    explanation: str
    feedback: str


class FollowupOut(BaseModel):
    revision_tasks: list[str]
    retry_on: date | None
    unplaced: int


class AttemptOut(BaseModel):
    id: str
    status: AttemptStatusOut
    score: int | None
    passed: bool | None
    results: list[ResultOut]
    followup: FollowupOut | None


class FlashcardOut(BaseModel):
    id: str
    front: str
    back: str
    skill: str | None
    due_date: date | None = None


class DueQueue(BaseModel):
    cards: list[FlashcardOut]
    reviewed_today: int
    daily_cards: int
    remaining_due: int  # due cards beyond today's queue (15 min)


class ReviewReceiptIn(BaseModel):
    id: UUID4
    due_date: date


class ReviewIn(BaseModel):
    result: Literal["ok", "fail"]
    receipt: ReviewReceiptIn | None = None


class ReviewOut(BaseModel):
    card_id: str
    step: int
    due_date: date
    demoted_skill: str | None


_Choice = Annotated[str, Field(min_length=1, max_length=200)]
_Criterion = Annotated[str, Field(min_length=1, max_length=200)]


class QuestionIn(BaseModel):
    """A question written by hand or by Claude, within the Examiner's bounds: an MCQ has 3 to 5
    distinct choices and the rank of the right one (`correct_index`); an open question (`short`,
    `code`, `explain`) has the expected answer and a rubric (1 to 4 criteria); `code` gives the
    snippet in `code`."""

    type: QuestionType
    prompt: str = Field(min_length=MIN_PROMPT_CHARS, max_length=600)
    code: str | None = Field(default=None, max_length=3000)
    choices: list[_Choice] = Field(default_factory=list, max_length=MAX_CHOICES)
    correct_index: int | None = None
    expected: str = Field(default="", max_length=800)
    rubric: list[_Criterion] = Field(default_factory=list, max_length=4)
    explanation: str = Field(default="", max_length=800)
    skill: str = Field(min_length=2, max_length=120)

    @model_validator(mode="after")
    def _shape(self) -> "QuestionIn":
        if self.type == "mcq":
            distinct = {" ".join(c.casefold().split()) for c in self.choices}
            ok = MIN_CHOICES <= len(self.choices) <= MAX_CHOICES and len(distinct) == len(
                self.choices
            )
            if (
                not ok
                or self.correct_index is None
                or not 0 <= self.correct_index < len(self.choices)
            ):
                raise ValueError("malformed MCQ")
            return self
        if self.choices or self.correct_index is not None:
            raise ValueError("only an MCQ has choices")
        if self.type == "code" and not (self.code or "").strip():
            raise ValueError("missing code snippet")
        if not self.expected.strip() or not self.rubric:
            raise ValueError("missing expected answer and rubric")
        return self


class QuestionPatch(BaseModel):
    """Edit of a question: the given fields replace the question's, which is then
    revalidated in full (`QuestionIn`)."""

    prompt: str | None = Field(default=None, min_length=MIN_PROMPT_CHARS, max_length=600)
    code: str | None = Field(default=None, max_length=3000)
    choices: list[_Choice] | None = Field(default=None, max_length=MAX_CHOICES)
    correct_index: int | None = None
    expected: str | None = Field(default=None, max_length=800)
    rubric: list[_Criterion] | None = Field(default=None, max_length=4)
    explanation: str | None = Field(default=None, max_length=800)
    skill: str | None = Field(default=None, min_length=2, max_length=120)

    @model_validator(mode="after")
    def _something(self) -> "QuestionPatch":
        if not self.model_dump(exclude_none=True):
            raise ValueError("nothing to change")
        return self


class QuizWriteIn(BaseModel):
    """A module quiz written directly (no agent): 1 to 12 questions. The module does not need a
    ready lesson. No review cards: writing them is a bulk query that the MCP history would not
    see."""

    module_id: str = Field(min_length=1, max_length=36)
    title: str = Field(min_length=3, max_length=200)
    questions: list[QuestionIn] = Field(min_length=1, max_length=MAX_QUESTIONS)


class QuizPatch(BaseModel):
    title: str = Field(min_length=3, max_length=200)
