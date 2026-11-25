"""Mock interview schemas (SPEC F10, D145): the Interviewer's plan, its decision after each
answer, the debrief and the context that the `interview` graph reads.

The lengths of a text read by January are shortened (`Prose`) instead of being refused; the
numbers (plan questions, scores, 1 to 5 scale) are checked by the code and sent back to the model
(`structured_call`). The question indices are those of the plan, from 0: the answers are given
in order, so question `i` of the exchange list is plan question `i`."""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, BeforeValidator, Field, field_validator, model_validator

from app.agents.runtime.prose import Prose, ShortenToMax, shorten
from app.agents.tools.cv_schema import CvContent, MasterProfileData
from app.agents.tools.kit_schema import CompanyDossier
from app.agents.tools.negotiation import SalarySample
from app.agents.tools.posting_schema import PostingAnalysis
from app.db.models.applications import InterviewMode

__all__ = [
    "CRITERIA",
    "QUESTIONS_BY_DURATION",
    "SCORE_KEYS",
    "Criterion",
    "Debrief",
    "Exchange",
    "ExpectedPoints",
    "InterviewContext",
    "InterviewPlan",
    "PlannedQuestion",
    "QuestionSource",
    "TurnDecision",
    "debrief_schema",
    "plan_schema",
]

QUESTIONS_BY_DURATION = {15: 4, 30: 7, 45: 10}  # main questions; one follow-up at most
Criterion = Literal["clarity", "structure", "technical_depth", "role_fit"]
QuestionSource = Literal["posting", "company_dossier", "cv", "gap", "general"]
ScoreKey = Criterion
CRITERIA: tuple[Criterion, ...] = ("clarity", "structure", "technical_depth", "role_fit")
SCORE_KEYS = CRITERIA
_LEGACY_CRITERIA = {"clarte": "clarity", "profondeur": "technical_depth", "adequation": "role_fit"}
_LEGACY_SOURCES = {"offre": "posting", "dossier": "company_dossier", "ecart": "gap"}
_LEGACY_SCORE_KEYS = {**_LEGACY_CRITERIA, "profondeur_technique": "technical_depth"}
Point = Annotated[str, Field(min_length=1, max_length=200), ShortenToMax()]
Sentence = Annotated[str, Field(min_length=1, max_length=300), ShortenToMax()]


def _read_criterion(value: object) -> object:
    return _LEGACY_CRITERIA.get(value, value) if isinstance(value, str) else value


def _read_source(value: object) -> object:
    return _LEGACY_SOURCES.get(value, value) if isinstance(value, str) else value


CheckpointCriterion = Annotated[Criterion, BeforeValidator(_read_criterion)]
CheckpointSource = Annotated[QuestionSource, BeforeValidator(_read_source)]


class PlannedQuestion(BaseModel):
    text: Prose = Field(min_length=5, max_length=400)
    criterion: CheckpointCriterion
    source: CheckpointSource


class InterviewPlan(BaseModel):
    questions: list[PlannedQuestion] = Field(min_length=1)


def plan_schema(count: int) -> type[InterviewPlan]:
    """The plan of exactly `count` questions, all different: an answer that departs from it
    is sent back to the model with the reason."""

    class Plan(InterviewPlan):
        questions: list[PlannedQuestion] = Field(min_length=count, max_length=count)

        @field_validator("questions")
        @classmethod
        def _distinct(cls, value: list[PlannedQuestion]) -> list[PlannedQuestion]:
            texts = {" ".join(q.text.casefold().split()) for q in value}
            if len(texts) != len(value):
                raise ValueError("two questions are identical: every question must be different")
            return value

    return Plan


class TurnDecision(BaseModel):
    """After an answer: a follow-up (or `None`) and the internal score of the answer (1 to 5)."""

    follow_up: str | None = Field(default=None, max_length=300)
    note: int = Field(ge=1, le=5)
    salary_move: bool = False

    @field_validator("follow_up", mode="before")
    @classmethod
    def _short_or_none(cls, value: object) -> object:
        if isinstance(value, str):
            return shorten(value.strip(), 300) or None
        return value


class Exchange(BaseModel):
    """A main question, January's answer, the follow-up if there was one (and its
    answer), the internal score (1 to 5) of the whole."""

    index: int = Field(ge=0)
    question: str
    criterion: CheckpointCriterion
    source: CheckpointSource
    answer: str
    follow_up: str | None = None
    follow_up_answer: str | None = None
    note: int = Field(ge=1, le=5)
    unrated: bool = False  # the model did not answer: the score is neutral, set by the code
    salary_raised: bool = False


class ExpectedPoints(BaseModel):
    """The points a good answer to question `index` would have given (back of the card)."""

    index: int = Field(ge=0)
    points: list[Point] = Field(min_length=1, max_length=4)


class Debrief(BaseModel):
    scores: dict[ScoreKey, int]  # 1 to 5, the four keys
    strengths: list[Sentence] = Field(min_length=3, max_length=3)
    fixes: list[Sentence] = Field(min_length=3, max_length=3)
    weakest_index: int = Field(ge=0)  # set by the code: the lowest internal score
    improved_answer: Prose = Field(min_length=1, max_length=1500)
    missed: list[int] = Field(default_factory=list)  # set by the code: scores <= 2
    expected: list[ExpectedPoints] = Field(default_factory=list)  # one per missed question
    unrated: list[int] = Field(default_factory=list)  # set by the code: unrated answers

    @field_validator("scores", mode="before")
    @classmethod
    def _read_checkpoint_scores(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        scores = dict(value)
        for old, new in _LEGACY_SCORE_KEYS.items():
            if old in scores:
                score = scores.pop(old)
                scores.setdefault(new, score)
        return scores

    @field_validator("scores")
    @classmethod
    def _four_scores(cls, value: dict[ScoreKey, int]) -> dict[ScoreKey, int]:
        if set(value) != set(SCORE_KEYS):
            raise ValueError("a score is needed for each of the four criteria")
        if any(not 1 <= score <= 5 for score in value.values()):
            raise ValueError("each score goes from 1 to 5")
        return value


def debrief_schema(missed: list[int]) -> type[Debrief]:
    """The debrief whose `expected` covers each missed question (`missed`, set by the code)."""

    class Checked(Debrief):
        @model_validator(mode="after")
        def _covers_missed(self) -> Self:
            given = {item.index for item in self.expected}
            absent = [index for index in missed if index not in given]
            if absent:
                raise ValueError(f"`expected` must cover the missed questions: {absent}")
            return self

    return Checked


class InterviewContext(BaseModel):
    """What the graph reads (read-only): the setting, the posting (text and analysis, absent from
    a free interview on a job title), the company dossier, the CV version sent, the known
    gaps and the validated profile."""

    mode: InterviewMode
    duration_min: Literal[15, 30, 45]
    language: Literal["fr", "en"]
    role: str
    posting_text: str | None = None
    analysis: PostingAnalysis | None = None
    dossier: CompanyDossier | None = None
    cv_content: CvContent | None = None
    gaps: list[str] = Field(default_factory=list)
    profile: MasterProfileData
    salary: SalarySample | None = None
    surprise: bool = False
