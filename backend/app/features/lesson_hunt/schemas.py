"""Public responses of the error hunt."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.agents.tools.lesson_hunt_port import ErrorEdit, HuntAssessment
from app.db.models.lesson_hunt import HuntStage

ResponseText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=4, max_length=2400)
]


class HuntCreate(BaseModel):
    lesson_id: str = Field(min_length=36, max_length=36)


class HuntAnswers(BaseModel):
    responses: list[ResponseText] = Field(min_length=2, max_length=2)


class HuntStarted(BaseModel):
    hunt_id: str
    session_id: str


class HuntOut(BaseModel):
    id: str
    lesson_id: str
    title: str
    stage: HuntStage | Literal["failed"]
    session_id: str
    exercise: str | None
    responses: list[str] | None
    corrections: list[ErrorEdit] | None
    assessment: HuntAssessment | None
