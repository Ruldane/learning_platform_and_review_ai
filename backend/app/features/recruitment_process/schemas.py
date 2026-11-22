from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.agents.tools.recruitment_process_port import (
    RecruitmentCriterion,
    RecruitmentGrade,
    RecruitmentKind,
)

RecruitmentState = Literal["ready", "evaluating", "failed", "complete"]


class RecruitmentChoice(BaseModel):
    id: str
    title: str


class RecruitmentOptions(BaseModel):
    postings: list[RecruitmentChoice]
    projects: list[RecruitmentChoice]


class RecruitmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    posting_id: UUID
    project_id: UUID | None = None


class RecruitmentAnswerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=8000)]


class RecruitmentMissingProof(BaseModel):
    requirement: str
    skills: list[str]


class RecruitmentStep(BaseModel):
    kind: RecruitmentKind
    prompt: str
    answer: str | None = None
    session_id: str | None = None
    grade: RecruitmentGrade | None = None
    graded_at: datetime | None = None


class RecruitmentOut(BaseModel):
    id: str
    posting_id: str
    posting_title: str
    company: str | None
    created_at: datetime
    project: RecruitmentChoice | None
    rubric: list[RecruitmentCriterion]
    missing_proofs: list[RecruitmentMissingProof]
    steps: list[RecruitmentStep]
    active_step: RecruitmentKind | None
    state: RecruitmentState


class RecruitmentStarted(BaseModel):
    session_id: str
