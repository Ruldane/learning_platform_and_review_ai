from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.agents.tools.grade_appeals_port import AppealReading
from app.db.models.grade_appeals import AppealDecision

AppealState = Literal["draft", "reviewing", "failed", "ready", "decided"]


class GradeAppealProject(BaseModel):
    id: str
    title: str


class GradeAppealCriterion(BaseModel):
    index: int
    criterion: str
    original_met: bool
    original_comment: str


class GradeAppealSource(BaseModel):
    project: GradeAppealProject
    criterion: GradeAppealCriterion
    submission: str
    submitted_at: datetime


class GradeAppealCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: UUID
    criterion_index: Annotated[int, Field(ge=1)]
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=3500)]


class GradeAppealDecisionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: AppealDecision


class GradeAppealOut(BaseModel):
    id: str
    created_at: datetime
    source: GradeAppealSource
    reason: str
    state: AppealState
    second: AppealReading | None
    reviewed_at: datetime | None
    decision: AppealDecision | None
    decided_at: datetime | None


class GradeAppealStarted(BaseModel):
    session_id: str
