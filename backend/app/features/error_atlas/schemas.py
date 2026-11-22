from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

SourceKind = Literal["quiz", "project"]
Confidence = Literal["low", "medium", "high"]
GroupConfidence = Literal["low", "medium", "high", "mixed"]
ResourceId = Annotated[str, StringConstraints(min_length=1, max_length=36)]
SourceId = Annotated[str, StringConstraints(min_length=1, max_length=64)]
Label = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]


class AtlasReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: SourceKind
    resource_id: ResourceId
    source_id: SourceId
    item_id: ResourceId


class AtlasEvidenceOut(BaseModel):
    reference: AtlasReference
    title: str
    finding: str
    expected: str | None
    recorded_at: datetime


class AtlasObservationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference: AtlasReference
    hypothesis: Label
    confidence: Confidence


class AtlasObservationOut(BaseModel):
    id: str
    evidence: AtlasEvidenceOut
    confidence: Confidence


class AtlasExerciseOut(BaseModel):
    id: str
    created_at: datetime
    steps: list[str]
    evidence: list[AtlasEvidenceOut]


class AtlasHypothesisOut(BaseModel):
    id: str
    label: str
    confidence: GroupConfidence
    observations: list[AtlasObservationOut]
    exercise: AtlasExerciseOut | None
