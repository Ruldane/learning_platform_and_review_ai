from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

OfferCriterion = Literal["match", "work_mode", "location"]
OfferWorkMode = Literal["remote", "hybrid", "onsite"]
OfferLeader = Literal["first", "second", "tie"]

_Weight = Annotated[int, Field(ge=0, le=100)]
_PointScore = Annotated[int, Field(ge=0, le=100)]


class OfferComparisonWeights(BaseModel):
    model_config = ConfigDict(extra="forbid")

    match: _Weight = 50
    work_mode: _Weight = 50
    location: _Weight = 50

    @model_validator(mode="after")
    def _positive(self) -> Self:
        if not (self.match or self.work_mode or self.location):
            raise ValueError("Au moins un poids doit être positif.")
        return self


class OfferComparisonPreferences(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weights: OfferComparisonWeights = Field(default_factory=OfferComparisonWeights)
    preferred_work_mode: OfferWorkMode | None = None
    preferred_location: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
        | None
    ) = None


class OfferComparisonPair(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_id: UUID
    second_id: UUID
    preferences: OfferComparisonPreferences | None = None

    @model_validator(mode="after")
    def _distinct(self) -> Self:
        if self.first_id == self.second_id:
            raise ValueError("Choisis deux offres distinctes.")
        return self


class OfferComparisonPosting(BaseModel):
    id: str
    title: str | None
    company: str | None


class OfferComparisonScores(BaseModel):
    match: _PointScore | None
    work_mode: _PointScore | None
    location: _PointScore | None


class OfferComparisonAssessment(OfferComparisonPosting):
    location: str | None
    remote: str | None
    scores: OfferComparisonScores
    missing: list[OfferCriterion]


class OfferWeightSensitivity(BaseModel):
    criterion: OfferCriterion
    lower_weight: int
    higher_weight: int
    lower_leader: OfferLeader | None
    higher_leader: OfferLeader | None
    lower_margin: float | None
    higher_margin: float | None


class OfferComparisonResult(BaseModel):
    preferences: OfferComparisonPreferences
    first: OfferComparisonAssessment
    second: OfferComparisonAssessment
    scored_criteria: list[OfferCriterion]
    first_score: float | None
    second_score: float | None
    leader: OfferLeader | None
    sensitivity: list[OfferWeightSensitivity]


class OfferComparisonSaved(BaseModel):
    id: str
    created_at: datetime
    result: OfferComparisonResult


class OfferComparisonHistoryItem(BaseModel):
    id: str
    created_at: datetime
    first: OfferComparisonPosting
    second: OfferComparisonPosting
