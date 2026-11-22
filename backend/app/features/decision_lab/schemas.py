from datetime import datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


class ArchitectureAssumptions(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    replicas: int = Field(ge=1, le=64)
    replica_capacity_rps: int = Field(ge=1, le=100_000)
    hourly_cost_cents: int = Field(ge=0, le=100_000)


class DecisionAssumptions(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    request_rate: int = Field(ge=0, le=100_000)
    duration_minutes: int = Field(ge=1, le=1440)
    outage_minutes: int = Field(ge=0, le=1440)
    architecture_a: ArchitectureAssumptions
    architecture_b: ArchitectureAssumptions

    @model_validator(mode="after")
    def _outage_fits_window(self) -> Self:
        if self.outage_minutes > self.duration_minutes:
            raise ValueError("La durée de la panne doit tenir dans la durée de l’essai.")
        return self


class DecisionMetrics(BaseModel):
    served_requests: int
    missed_requests: int
    served_basis_points: int | None
    cost_cents: int


class DecisionComparison(BaseModel):
    attempted_requests: int
    architecture_a: DecisionMetrics
    architecture_b: DecisionMetrics


class DecisionScenarioCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    assumptions: DecisionAssumptions
    critique: str = Field(default="", max_length=2000)


class DecisionScenarioSummary(BaseModel):
    id: UUID
    title: str
    created_at: datetime


class DecisionScenarioOut(DecisionScenarioSummary):
    assumptions: DecisionAssumptions
    results: DecisionComparison
    critique: str
