from typing import Literal

from pydantic import BaseModel, Field

from app.agents.tools.oncall_port import ReviewScore
from app.features.oncall.scenarios import ScenarioKind

DiagnosticState = Literal["idle", "running", "passed", "failed", "stale"]


class IncidentCreate(BaseModel):
    kind: ScenarioKind | None = None
    seed: int | None = Field(default=None, ge=0, le=999_999)


class IncidentEvent(BaseModel):
    id: str
    minute: int
    kind: Literal["sample", "alert", "diagnostic"]
    metric: ScenarioKind
    value: int


class IncidentSummary(BaseModel):
    id: str
    kind: ScenarioKind
    title: str
    seed: int
    minute: int
    alerted: bool
    ide_session_id: str
    proof_recorded: bool


class DiagnosticView(BaseModel):
    state: DiagnosticState
    run_id: str | None = None


class IncidentView(IncidentSummary):
    events: list[IncidentEvent]
    observed_events: list[str]
    diagnostic: DiagnosticView
    report: str | None = None
    review_session_id: str | None = None
    review_state: Literal["idle", "running", "failed", "complete"] = "idle"
    verdict: ReviewScore | None = None


class OncallReportIn(BaseModel):
    text: str = Field(min_length=8, max_length=6_000)


class OncallReviewStarted(BaseModel):
    session_id: str
