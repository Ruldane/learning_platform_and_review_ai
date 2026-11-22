from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.routines import RoutineAction
from app.features.dated_commitments.service.reminders import CommitmentReminder

LocalTime = Annotated[str, Field(pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")]


class RoutineIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: RoutineAction
    local_time: LocalTime


class RoutinePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    local_time: LocalTime | None = None


class RoutineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    action: RoutineAction
    local_time: LocalTime
    enabled: bool


class ExecutionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    receipt: UUID


class ExecutionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    routine_id: UUID
    source: Literal["manual", "scheduled"]
    result_count: int
    notices: list[CommitmentReminder]
    created_at: datetime
