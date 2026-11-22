"""Schémas de l'entretien blanc (SPEC F10, D145) : le plan de l'Intervieweur, sa décision après
chaque réponse, le débrief et le contexte que le parcours `interview` lit.

Les longueurs d'un texte lu par January sont raccourcies (`Prose`) au lieu d'être refusées ; les
nombres (questions du plan, notes, échelle 1 à 5) sont vérifiés par le code et renvoyés au modèle
(`structured_call`). Les indices des questions sont ceux du plan, à partir de 0 : les réponses sont
données dans l'ordre, la question `i` de la liste des échanges est donc celle du plan `i`."""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator

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

QUESTIONS_BY_DURATION = {15: 4, 30: 7, 45: 10}  # questions principales ; une relance au plus
Criterion = Literal["clarte", "structure", "profondeur", "adequation"]
QuestionSource = Literal["offre", "dossier", "cv", "ecart", "general"]
ScoreKey = Literal["clarte", "structure", "profondeur_technique", "adequation"]
CRITERIA: tuple[Criterion, ...] = ("clarte", "structure", "profondeur", "adequation")
SCORE_KEYS: tuple[ScoreKey, ...] = ("clarte", "structure", "profondeur_technique", "adequation")
Point = Annotated[str, Field(min_length=1, max_length=200), ShortenToMax()]
Sentence = Annotated[str, Field(min_length=1, max_length=300), ShortenToMax()]


class PlannedQuestion(BaseModel):
    text: Prose = Field(min_length=5, max_length=400)
    criterion: Criterion
    source: QuestionSource


class InterviewPlan(BaseModel):
    questions: list[PlannedQuestion] = Field(min_length=1)


def plan_schema(count: int) -> type[InterviewPlan]:
    """Le plan d'exactement `count` questions, toutes différentes : une réponse qui s'en écarte
    est renvoyée au modèle avec le motif."""

    class Plan(InterviewPlan):
        questions: list[PlannedQuestion] = Field(min_length=count, max_length=count)

        @field_validator("questions")
        @classmethod
        def _distinct(cls, value: list[PlannedQuestion]) -> list[PlannedQuestion]:
            texts = {" ".join(q.text.casefold().split()) for q in value}
            if len(texts) != len(value):
                raise ValueError("deux questions sont identiques : chaque question est différente")
            return value

    return Plan


class TurnDecision(BaseModel):
    """Après une réponse : une relance (ou `None`) et la note interne de la réponse (1 à 5)."""

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
    """Une question principale, la réponse de January, la relance s'il y en a eu une (et sa
    réponse), la note interne (1 à 5) de l'ensemble."""

    index: int = Field(ge=0)
    question: str
    criterion: Criterion
    source: QuestionSource
    answer: str
    follow_up: str | None = None
    follow_up_answer: str | None = None
    note: int = Field(ge=1, le=5)
    unrated: bool = False  # le modèle n'a pas répondu : la note est neutre, posée par le code
    salary_raised: bool = False


class ExpectedPoints(BaseModel):
    """Les points qu'une bonne réponse à la question `index` aurait donnés (verso de la fiche)."""

    index: int = Field(ge=0)
    points: list[Point] = Field(min_length=1, max_length=4)


class Debrief(BaseModel):
    scores: dict[ScoreKey, int]  # 1 à 5, les quatre clés
    strengths: list[Sentence] = Field(min_length=3, max_length=3)
    fixes: list[Sentence] = Field(min_length=3, max_length=3)
    weakest_index: int = Field(ge=0)  # fixé par le code : la note interne la plus basse
    improved_answer: Prose = Field(min_length=1, max_length=1500)
    missed: list[int] = Field(default_factory=list)  # fixé par le code : notes ≤ 2
    expected: list[ExpectedPoints] = Field(default_factory=list)  # une par question ratée
    unrated: list[int] = Field(default_factory=list)  # fixé par le code : réponses non notées

    @field_validator("scores")
    @classmethod
    def _four_scores(cls, value: dict[ScoreKey, int]) -> dict[ScoreKey, int]:
        if set(value) != set(SCORE_KEYS):
            raise ValueError("il faut une note pour chacun des quatre critères")
        if any(not 1 <= score <= 5 for score in value.values()):
            raise ValueError("chaque note va de 1 à 5")
        return value


def debrief_schema(missed: list[int]) -> type[Debrief]:
    """Le débrief dont `expected` couvre chaque question ratée (`missed`, fixé par le code)."""

    class Checked(Debrief):
        @model_validator(mode="after")
        def _covers_missed(self) -> Self:
            given = {item.index for item in self.expected}
            absent = [index for index in missed if index not in given]
            if absent:
                raise ValueError(f"`expected` doit couvrir les questions ratées : {absent}")
            return self

    return Checked


class InterviewContext(BaseModel):
    """Ce que le parcours lit (lecture seule) : le réglage, l'offre (texte et analyse, absents d'un
    entretien libre sur un intitulé), le dossier de l'entreprise, la version du CV envoyée, les
    écarts connus et le profil validé."""

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
