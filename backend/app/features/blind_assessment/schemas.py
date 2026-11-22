"""Entrées de l’épreuve et projection publique après verdict."""

from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from app.agents.tools.blind_assessment_port import BlindCriterion, BlindGrade

RubricId = Literal["clarity", "evidence"]


class BlindRubric(BaseModel):
    id: RubricId
    title: str
    criteria: list[BlindCriterion]


class BlindSourceOption(BaseModel):
    id: str
    label: str
    created_at: datetime


class BlindSourceLink(BaseModel):
    id: str
    label: str
    url: str


class BlindOptions(BaseModel):
    sources: list[BlindSourceOption]
    rubrics: list[BlindRubric]


class BlindCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    first_version_id: UUID
    second_version_id: UUID
    rubric: RubricId

    @model_validator(mode="after")
    def distinct_versions(self) -> Self:
        if self.first_version_id == self.second_version_id:
            raise ValueError("Choisis deux versions différentes.")
        return self


class BlindResultOut(BlindGrade):
    source_a: BlindSourceLink
    source_b: BlindSourceLink
    evaluated_at: datetime
    verdict: Literal["a", "b", "tie"]


class BlindOut(BaseModel):
    id: str
    created_at: datetime
    rubric: BlindRubric
    stage: Literal["draft", "evaluating", "failed", "complete"]
    result: BlindResultOut | None


class BlindStarted(BaseModel):
    session_id: str
