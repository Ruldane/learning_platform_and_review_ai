"""Contrat du radar du marché (SPEC 14.2, P10, D160). Le poste et la zone sont des données
personnelles : une 422 nomme les champs, sans jamais les recopier (route à `FieldPathsRoute`)."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, StringConstraints

from app.db.models.daily import RadarStatus, RadarTrigger

Label = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]


class RadarRunIn(BaseModel):
    """Poste et zone du relevé ; absents : ceux des réglages, puis du dernier objectif."""

    role: Label | None = None
    zone: Label | None = None


class RunStarted(BaseModel):
    run_id: str
    session_id: str


class RunRef(BaseModel):
    id: str
    created_at: datetime


class DomainCount(BaseModel):
    domain: str
    count: int


class TrendOut(BaseModel):
    """Une compétence du classement. `delta_share` : points de pourcentage depuis le relevé
    précédent ; `delta_rank` : rangs gagnés (positif) ou perdus ; `None` sans relevé précédent."""

    skill: str
    count: int
    share: float
    rank: int
    delta_share: int | None
    delta_rank: int | None
    new: bool


class RadarAlertOut(BaseModel):
    skill: str
    share: float
    message: str


class OfferOut(BaseModel):
    url: str
    title: str | None
    company: str | None
    level: str
    remote: str | None
    salary: str | None
    score: int


class RadarRunSummary(BaseModel):
    id: str
    role: str
    zone: str
    status: RadarStatus
    trigger: RadarTrigger
    created_at: datetime
    finished_at: datetime | None
    error_code: str | None
    read_count: int
    not_postings: int
    blocked_count: int
    analyzed: int
    low_sample: bool


class RadarRunOut(RadarRunSummary):
    """Un relevé, avec les nombres réels. `read_count` : pages lisibles ; `not_postings` : celles
    qui n'étaient pas des offres ; `analyzed` : offres analysées ; `not_analyzed` : offres lues
    mais pas analysées (extraction en échec, ou au-delà des 50 lues d'un relevé) : l'écart ne se
    cache jamais (« 55 lues, 50 analysées »)."""

    not_analyzed: int
    blocked_domains: list[DomainCount]
    ranking: list[TrendOut]
    alerts: list[RadarAlertOut]
    offers: list[OfferOut]
    previous: RunRef | None


class RadarDefaults(BaseModel):
    role: str
    zone: str


class RadarLatestOut(BaseModel):
    defaults: RadarDefaults
    running: RunRef | None
    latest: RadarRunOut | None
