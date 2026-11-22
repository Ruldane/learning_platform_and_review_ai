"""Schémas des entretiens blancs (SPEC F10, D146). Une 422 nomme les champs (`details.fields`),
jamais leur valeur : l'intitulé du poste, les réponses et le débrief sont des données personnelles.

`status` : `running` (en cours), `done` (débrief écrit), `stopped` (arrêté avant toute réponse),
`debrief_failed` (les réponses sont gardées, le débrief n'a pas pu être écrit : ni notes, ni
fiches), `failed` (la session s'est terminée sans résultat)."""

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
    """Le réglage d'un entretien : la formule (comportemental, technique, étude de cas, mixte), la
    durée (4, 7 ou 10 questions principales) et la langue des questions."""

    mode: InterviewMode
    duration_min: Literal[15, 30, 45]
    language: Literal["fr", "en"] = "fr"
    radar_role: RadarLabel | None = None
    radar_zone: RadarLabel | None = None


class FreeInterviewIn(InterviewIn):
    """Un entretien sans fiche : sur une offre (`posting_id`) ou sur un intitulé seul (`role`).
    L'un ou l'autre, pas les deux ni aucun (422 `fields: ["posting_id", "role"]`)."""

    posting_id: Id | None = None
    role: Role | None = None


class InterviewStartOut(BaseModel):
    interview_id: str
    session_id: str


class ExchangeOut(BaseModel):
    """Une question principale, la réponse de January, la relance et sa réponse s'il y en a eu, la
    note interne (1 à 5) ; `unrated` : le modèle n'a pas répondu, la note est neutre."""

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
    """Les points qu'une bonne réponse à la question `index` aurait donnés (verso de la fiche)."""

    index: int
    points: list[str]


class DebriefOut(BaseModel):
    """Le débrief : quatre notes (1 à 5), trois points forts, trois corrections, la réponse
    améliorée de la question `weakest_index` (à vérifier si `flags` n'est pas vide), les questions
    ratées (`missed`, note interne 2 au plus) et leurs points attendus, les réponses non
    notées (`unrated`)."""

    scores: dict[ScoreKey, int]
    strengths: list[str]
    fixes: list[str]
    weakest_index: int
    improved_answer: str
    missed: list[int]
    expected: list[ExpectedOut]
    unrated: list[int]


class InterviewOut(BaseModel):
    """Un entretien. `flags` : les termes que le profil ne dit pas dans la réponse améliorée.
    `cards_created` : les fiches de révision nouvelles (une par question ratée, dues demain)."""

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
