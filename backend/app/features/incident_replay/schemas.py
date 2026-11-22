from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class IncidentScenarioOut(BaseModel):
    key: str
    title: str
    context: str


class IncidentEvent(BaseModel):
    minute: int
    title: str
    observed: str


class IncidentReplayIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario: Annotated[str, Field(min_length=1, max_length=48)]
    receipt: UUID


class IncidentNote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step: Annotated[int, Field(ge=0, le=100)]
    hypothesis: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1500)
    ]


class IncidentReplayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    scenario: str
    title: str
    timeline: list[IncidentEvent]
    notes: list[IncidentNote]
    created_at: datetime
