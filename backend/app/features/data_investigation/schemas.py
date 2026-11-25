from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

Operation = Literal["latest_revision", "delivered_only", "declared_identifier", "positive_units"]
DatasetKey = Literal["deliveries-v1", "supplies-v1"]


class InvestigationRow(BaseModel):
    source_row: int
    reference: str
    revision: int
    status: Literal["delivered", "pending", "cancelled"]
    units: int


class InvestigationDataset(BaseModel):
    key: DatasetKey
    title: str
    brief: str


class InvestigationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset: DatasetKey


class InvestigationOperations(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operations: Annotated[list[Operation], Field(max_length=4)]

    @model_validator(mode="after")
    def unique(self) -> Self:
        if len(set(self.operations)) != len(self.operations):
            raise ValueError("An operation can only be added once.")
        return self


class InvestigationStep(BaseModel):
    operation: Operation
    removed_rows: list[int]
    remaining_rows: int


class InvestigationMetrics(BaseModel):
    units: int
    deliveries: int


class InvestigationSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")

    units: Annotated[int, Field(ge=0, le=100000)]
    deliveries: Annotated[int, Field(ge=0, le=1000)]


class InvestigationResult(BaseModel):
    submission: InvestigationSubmission
    expected: InvestigationMetrics
    matches_pipeline: bool
    integrity_passed: bool


class InvestigationOut(BaseModel):
    id: UUID
    dataset: InvestigationDataset
    source_rows: list[InvestigationRow]
    source_digest: str
    operations: list[Operation]
    trace: list[InvestigationStep]
    preview: InvestigationMetrics
    retained_rows: list[int]
    result: InvestigationResult | None
    created_at: datetime


class InvestigationSummary(BaseModel):
    id: UUID
    title: str
    completed: bool
    created_at: datetime
