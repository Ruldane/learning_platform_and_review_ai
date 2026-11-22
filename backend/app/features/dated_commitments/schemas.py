from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Version = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
Intention = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1500)]
Indicator = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
Unit = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
Note = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1500)]
Measure = Annotated[
    Decimal,
    Field(allow_inf_nan=False, max_digits=12, decimal_places=4, ge=-10_000_000, le=10_000_000),
]


class CommitmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    title: Title
    version: Version
    intention: Intention
    indicator: Indicator
    unit: Unit
    target: Measure
    due_on: date


class CommitmentReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observed: Measure
    note: Note | None = None


class CommitmentReminder(BaseModel):
    id: str
    title: str
    version: str
    intention: str
    due_on: date
    indicator: str
    unit: str
    delta: Decimal | None
    reviewed: bool


class CommitmentOut(CommitmentReminder):
    status: Literal["scheduled", "due", "reviewed"]
    target: Decimal
    observed: Decimal | None
    note: str | None
    created_at: datetime
    reviewed_at: datetime | None
