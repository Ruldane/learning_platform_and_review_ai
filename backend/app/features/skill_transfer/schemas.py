"""Public contract of the checks, with a statement distinct from the marking grid."""

from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.core.skills import EvidenceKind
from app.db.models.skill_transfer import TransferStage


class ProofOption(BaseModel):
    id: str
    skill_id: str
    skill_name: str
    kind: EvidenceKind
    label: str
    at: str | None


class TransferIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    skill_id: UUID
    proof_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    due_on: date


class AnswerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=8000)]


class TransferExerciseOut(BaseModel):
    title: str
    prompt: str


class AssessmentOut(BaseModel):
    verdict: Literal["demonstrated", "needs_review"]
    criteria: list[str]
    met: list[bool]
    feedback: str
    assessed_at: datetime


class TransferOut(BaseModel):
    id: str
    proof: ProofOption
    due_on: date
    available: bool
    stage: TransferStage
    retry: Literal["prepare", "answer"] | None = None
    session_id: str | None
    exercise: TransferExerciseOut | None = None
    answer: str | None = None
    assessment: AssessmentOut | None = None


class TransferStarted(BaseModel):
    transfer_id: str
    session_id: str
