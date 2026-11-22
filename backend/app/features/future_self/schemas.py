"""Entrée et résultat de la lecture Ton futur toi."""

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.features.future_self.projection import Recommendation, Scenario, Uncertainty

_Label = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
_Id = Annotated[str, StringConstraints(min_length=1, max_length=36)]


class FutureSelfQuery(BaseModel):
    role: _Label | None = None
    zone: _Label | None = None
    program_id: _Id | None = None
    alternative_weekly_minutes: int | None = Field(default=None, ge=0, le=7 * 24 * 60)
    target_percent: int = Field(default=60, ge=1, le=100)


class ProjectionSampleOut(BaseModel):
    run_id: str
    finished_at: datetime
    analyzed: int


class FutureSelfOut(BaseModel):
    as_of: date
    role: str | None
    zone: str
    program_id: str | None
    sample: ProjectionSampleOut | None
    offer_count: int
    current_percent: int | None
    target_percent: int
    observed_weeks: int
    scenarios: tuple[Scenario, ...]
    recommendations: tuple[Recommendation, ...]
    uncertainty: tuple[Uncertainty, ...]
