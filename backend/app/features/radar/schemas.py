"""Market radar contract (SPEC 14.2, P10, D160). The role and the zone are personal data: a
422 names the fields, never copying them back (route with `FieldPathsRoute`)."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, StringConstraints

from app.agents.tools.posting_schema import PostingLevel
from app.db.models.daily import RadarStatus, RadarTrigger

Label = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]


class RadarRunIn(BaseModel):
    """Role and zone of the run; when absent: those of the settings, then of the last goal."""

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
    """A skill of the ranking. `delta_share`: percentage points since the previous run;
    `delta_rank`: ranks gained (positive) or lost; `None` without a previous run."""

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
    level: PostingLevel
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
    """A run, with the real numbers. `read_count`: readable pages; `not_postings`: those that
    were not postings; `analyzed`: postings analyzed; `not_analyzed`: postings read but not
    analyzed (extraction failed, or beyond the 50 read in a run): the gap is never hidden
    ("55 read, 50 analyzed")."""

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
