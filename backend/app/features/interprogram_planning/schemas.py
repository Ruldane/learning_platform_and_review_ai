from datetime import date, datetime, timedelta
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

Issue = Literal["no_tasks", "weekly_budget", "program_budget", "prerequisites", "capacity"]
PrerequisiteState = Literal["completed", "planned", "pending", "unmatched"]
ProposalState = Literal["pending", "blocked", "accepted"]


class SharedWeekCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    week_start: date
    program_ids: list[UUID] = Field(min_length=2, max_length=5)

    @model_validator(mode="after")
    def valid_selection(self) -> Self:
        if self.week_start.weekday() != 0 or self.week_start > date.max - timedelta(days=7):
            raise ValueError("La semaine doit commencer un lundi.")
        if len(set(self.program_ids)) != len(self.program_ids):
            raise ValueError("Choisis des programmes distincts.")
        return self


class SharedWeekAccept(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmed: StrictBool

    @model_validator(mode="after")
    def must_confirm(self) -> Self:
        if not self.confirmed:
            raise ValueError("Confirme l’application de cette semaine.")
        return self


class SharedWeekOption(BaseModel):
    id: str
    title: str


class SharedWeekDay(BaseModel):
    date: date
    capacity_minutes: int
    reserved_minutes: int
    planned_minutes: int


class SharedTaskRef(BaseModel):
    task_id: str
    program_id: str
    module_id: str
    module_title: str
    title: str
    from_date: date
    minutes: int


class SharedPlacement(SharedTaskRef):
    planned_date: date


class SharedModuleRef(BaseModel):
    id: str
    program_id: str
    title: str


class SharedPrerequisite(BaseModel):
    module: SharedModuleRef
    label: str
    references: list[SharedModuleRef]
    status: PrerequisiteState


class SharedWeekSnapshot(BaseModel):
    week_start: date
    programs: list[SharedWeekOption]
    cap_minutes: int
    planned_minutes: int
    days: list[SharedWeekDay]
    placements: list[SharedPlacement]
    prerequisites: list[SharedPrerequisite]
    unplaced: list[SharedTaskRef]
    issues: list[Issue]


class SharedWeekOut(SharedWeekSnapshot):
    id: str
    created_at: datetime
    accepted_at: datetime | None
    status: ProposalState
