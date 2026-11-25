"""Replanning contract (SPEC F13, D106): January's request ("this week I only have 5 hours"),
plan version history. The diff schemas carry their own names (`VersionDiffOut`,
`VersionMoveOut`), same fields as the program's `PlanDiffOut` (F8)."""

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.db.models.program import PlanKind, PlanStatus

# The model's values, never copied: a status added later would not cause a 500 on
# `GET /versions` (review 5.9 m6, final review of phase 5). Contract unchanged.
PlanKindOut = PlanKind
PlanStatusOut = PlanStatus


class ReplanRequest(BaseModel):
    available_minutes: int | None = Field(default=None, ge=60, le=10080)
    message: str | None = Field(default=None, max_length=1000)


class ReplanStarted(BaseModel):
    session_id: str


class VersionMoveOut(BaseModel):
    task: str  # "{module} / {task}"
    before: date
    after: date


class VersionDiffOut(BaseModel):
    added: list[str]
    removed: list[str]
    moved: list[VersionMoveOut]
    weeks_before: int
    weeks_after: int


class WeekLoadOut(BaseModel):
    """Load of an affected week, before and after the proposal, and its cap."""

    rank: int
    start_date: date
    before: int
    after: int
    cap: int


class PlanVersionOut(BaseModel):
    """A plan version. `pending`: proposal waiting for January (in its session);
    `empty` and `impossible`: proposals closed as soon as written, never to validate."""

    version: int
    kind: PlanKindOut
    status: PlanStatusOut
    reason: str
    created_at: datetime
    accepted_at: datetime | None
    session_id: str | None
    review: str | None  # text of the review that triggered it
    diff: VersionDiffOut | None
    week_loads: list[WeekLoadOut]
