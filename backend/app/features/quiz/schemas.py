"""Contrat des quiz et des révisions (SPEC F9, D101). La bonne réponse, la grille et
l'explication d'une question ne sortent qu'avec la note d'une tentative (`ResultOut`)."""

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

QuizStatusOut = Literal["generating", "ready", "failed"]
AttemptStatusOut = Literal["grading", "graded", "failed"]
QuestionTypeOut = Literal["qcm", "short", "code", "explain"]


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
    rank: int  # rang affiché (questions mélangées au nouvel essai, F27)
    type: QuestionTypeOut
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
    choice: int | None = None  # rang du choix tel qu'affiché (QCM seulement)
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
    remaining_due: int  # fiches dues au-delà de la file du jour (15 min)


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
    """Une question écrite à la main ou par Claude, aux bornes de celles de l'Examinateur : un QCM
    a 3 à 5 choix distincts et le rang du bon (`correct_index`) ; une question ouverte (`short`,
    `code`, `explain`) a la réponse attendue et une grille (1 à 4 critères) ; `code` donne
    l'extrait dans `code`."""

    type: Literal["qcm", "short", "code", "explain"]
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
        if self.type == "qcm":
            distinct = {" ".join(c.casefold().split()) for c in self.choices}
            ok = MIN_CHOICES <= len(self.choices) <= MAX_CHOICES and len(distinct) == len(
                self.choices
            )
            if (
                not ok
                or self.correct_index is None
                or not 0 <= self.correct_index < len(self.choices)
            ):
                raise ValueError("QCM mal formé")
            return self
        if self.choices or self.correct_index is not None:
            raise ValueError("seul un QCM a des choix")
        if self.type == "code" and not (self.code or "").strip():
            raise ValueError("extrait de code manquant")
        if not self.expected.strip() or not self.rubric:
            raise ValueError("réponse attendue et grille manquantes")
        return self


class QuestionPatch(BaseModel):
    """Retouche d'une question : les champs donnés remplacent ceux de la question, qui est
    revalidée en entier (`QuestionIn`)."""

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
            raise ValueError("rien à changer")
        return self


class QuizWriteIn(BaseModel):
    """Le quiz d'un module écrit en direct (aucun agent) : de 1 à 12 questions. Le module n'a pas
    besoin d'une leçon prête. Pas de fiches de révision : leur écriture est une requête en masse que
    l'historique du MCP ne verrait pas."""

    module_id: str = Field(min_length=1, max_length=36)
    title: str = Field(min_length=3, max_length=200)
    questions: list[QuestionIn] = Field(min_length=1, max_length=MAX_QUESTIONS)


class QuizPatch(BaseModel):
    title: str = Field(min_length=3, max_length=200)
