"""Contrat de la bourse des compétences pour un poste et une zone."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, StringConstraints

from app.features.skills.service import SkillLevel

Label = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]


class MarketQuery(BaseModel):
    role: Label | None = None
    zone: Label | None = None
    skill: Label | None = None


class MarketSample(BaseModel):
    run_id: str
    finished_at: datetime
    analyzed: int


class SkillQuote(BaseModel):
    name: str
    key: str
    level: SkillLevel | None
    demand_percent: float
    change_points: float | None
    opportunity: bool


class HourSimulation(BaseModel):
    skill: str
    chapter: str | None
    lesson_id: str | None
    remaining_minutes: int | None
    progress_percent: int | None
    covered_before: int
    covered_after: int | None


class SkillMarketOut(BaseModel):
    role: str
    zone: str
    current: MarketSample | None
    previous: MarketSample | None
    quotes: tuple[SkillQuote, ...] = ()
    simulation: HourSimulation | None = None
    indicative: bool = False
