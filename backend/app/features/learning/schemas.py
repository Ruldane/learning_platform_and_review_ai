"""Learning API schemas (D87): goals, Council proposals, path choice and board states."""

from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.db.models.agents import SessionStatus
from app.db.models.learning import BoardKind, GoalStatus

# Literal types are re-exported: a router does not import `app.db` (contract 1b).
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
    """The goal entered by January (SPEC 3.1, step 1). A past deadline is refused (422, field
    path only, never the input)."""

    text: _GoalText
    target_role: _Role | None = None
    deadline: date | None = None
    weekly_hours: int | None = Field(default=None, ge=1, le=40)

    @field_validator("deadline")
    @classmethod
    def _not_past(cls, value: date | None) -> date | None:
        if value is not None and value < date.today():
            raise ValueError("The deadline has already passed.")
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
    session_id: str  # `learning_council` session started for this goal


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
    """`mix_with`: second proposal from the same batch (mix); `start_date`: desired program
    start, a Monday, today or later (otherwise 422 `invalid_start_date`); next Monday by
    default."""

    mix_with: _Id | None = None
    start_date: date | None = None


class ChooseOut(BaseModel):
    """`already_chosen`: this same choice was already made (double click, generic resume); the
    request changed nothing, `start_date` included (D87). Also false when this same choice
    restarts the Strategist, whose session failed without a program (D97)."""

    council_session_id: str
    status: SessionStatus
    already_chosen: bool = False


class BoardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    goal_id: str | None
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
    """Excalidraw scene edited by January (`serializeAsJSON`) and its note, sent back to the
    agents as a message. Body capped at 2 MiB (`core.body_limits.BOARD_BODY_MAX`)."""

    scene: dict[str, Any]
    note: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
