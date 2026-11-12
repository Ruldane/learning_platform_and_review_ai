"""Schémas de l'API de l'apprentissage (D87) : objectifs, propositions du Conseil, choix du
parcours et états du tableau."""

from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.db.models.agents import SessionStatus
from app.db.models.learning import BoardKind, GoalStatus

# Les types littéraux sont réexportés : un router n'importe pas `app.db` (contrat 1b).
__all__ = [
    "BoardEdit",
    "BoardKind",
    "BoardOut",
    "ChooseOut",
    "ChooseRequest",
    "GoalCreate",
    "GoalOut",
    "GoalStarted",
    "GoalStatus",
    "ProposalOut",
    "SessionStatus",
]

_GoalText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=500)]
_Role = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
_Id = Annotated[str, Field(min_length=1, max_length=36)]


class GoalCreate(BaseModel):
    """L'objectif saisi par January (SPEC 3.1, étape 1). Une échéance passée est refusée (422,
    chemin du champ seulement, jamais la saisie)."""

    text: _GoalText
    target_role: _Role | None = None
    deadline: date | None = None
    weekly_hours: int | None = Field(default=None, ge=1, le=40)

    @field_validator("deadline")
    @classmethod
    def _not_past(cls, value: date | None) -> date | None:
        if value is not None and value < date.today():
            raise ValueError("L'échéance est déjà passée.")
        return value


class GoalOut(BaseModel):
    id: str
    text: str
    target_role: str | None
    deadline: date | None
    weekly_hours: int | None
    status: GoalStatus
    council_session_id: str | None
    program_id: str | None
    program_session_id: str | None
    created_at: datetime


class GoalStarted(BaseModel):
    goal: GoalOut
    session_id: str  # session `learning_council` lancée pour cet objectif


class ProposalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    goal_id: str
    batch: int
    rank: int
    name: str
    promise: str
    duration_weeks: int
    weekly_hours: int
    skills: list[str]
    final_project: str
    tradeoffs: list[str]
    board_id: str | None
    chosen: bool


class ChooseRequest(BaseModel):
    """`mix_with` : seconde proposition du même lot (mélange) ; `start_date` : début souhaité du
    programme (prochain lundi par défaut)."""

    mix_with: _Id | None = None
    start_date: date | None = None


class ChooseOut(BaseModel):
    council_session_id: str
    status: SessionStatus


class BoardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    goal_id: str
    session_id: str | None
    step: int
    kind: BoardKind
    title: str
    mermaid: str
    scene: dict[str, Any] | None
    author: Literal["scribe", "user"]
    parent_id: str | None
    created_at: datetime


class BoardEdit(BaseModel):
    """Scène Excalidraw retouchée par January (`serializeAsJSON`) et sa note, renvoyée aux agents
    comme un message. Corps plafonné à 2 Mio (`main.BOARD_BODY_MAX`)."""

    scene: dict[str, Any]
    note: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
