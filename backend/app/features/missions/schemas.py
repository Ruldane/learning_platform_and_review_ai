from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Index = Annotated[int, Field(strict=True, ge=0)]
Observation = Annotated[int, Field(strict=True, ge=0, le=2)]
Note = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
Artifact = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=8000)]
MissionLevel = Literal["not_started", "in_progress", "achieved"]
MissionStatus = Literal["active", "expired", "completed"]


class MissionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    posting_id: UUID
    requirement_indices: list[Index] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def unique_requirements(self) -> Self:
        if len(set(self.requirement_indices)) != len(self.requirement_indices):
            raise ValueError("Choisis des exigences distinctes.")
        return self


class MissionProgress(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision: Index
    observed: Observation
    note: Note | None = None


class MissionSubmit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision: Index
    artifact: Artifact


class Criterion(BaseModel):
    index: Index
    text: str
    required: bool
    skills: list[str]
    observed: Observation
    note: Note | None


class MissionCriterionOut(Criterion):
    target: Literal[2]
    level: MissionLevel


class MissionSubmissionOut(BaseModel):
    proof_id: str
    artifact: str
    recorded_at: datetime


class MissionOut(BaseModel):
    id: str
    posting_id: str
    posting_title: str | None
    company: str | None
    created_at: datetime
    deadline_at: datetime
    revision: int
    criteria: list[MissionCriterionOut]
    status: MissionStatus
    submission: MissionSubmissionOut | None
