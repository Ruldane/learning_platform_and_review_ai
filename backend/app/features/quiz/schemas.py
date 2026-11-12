"""Contrat des quiz et des révisions (SPEC F9, D101). La bonne réponse, la grille et
l'explication d'une question ne sortent qu'avec la note d'une tentative (`ResultOut`)."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

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


class DueQueue(BaseModel):
    cards: list[FlashcardOut]
    reviewed_today: int
    daily_cards: int
    remaining_due: int  # fiches dues au-delà de la file du jour (15 min)


class ReviewIn(BaseModel):
    result: Literal["ok", "fail"]


class ReviewOut(BaseModel):
    card_id: str
    step: int
    due_date: date
    demoted_skill: str | None
