from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.features.conversations.service import ConversationOut
from app.features.study.schemas import SkillLevelOut, StudyModeIn

LessonIds = Annotated[list[UUID], Field(max_length=8)]


class TrainingStart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: StudyModeIn = "socratic"
    new_conversation: bool = False
    lesson_ids: LessonIds = Field(default_factory=list)


class TrainingModeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["mode"]
    mode: StudyModeIn


class TrainingLessonsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["lessons"]
    lesson_ids: LessonIds


class TrainingFinish(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["finish"]
    worked_minutes: int | None = Field(default=None, ge=0, le=600)


class TrainingCancel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["cancel"]


TrainingContextUpdate = Annotated[
    TrainingModeUpdate | TrainingLessonsUpdate, Field(discriminator="action")
]
TrainingUpdate = Annotated[
    TrainingModeUpdate | TrainingLessonsUpdate | TrainingFinish | TrainingCancel,
    Field(discriminator="action"),
]


class TrainingSessionOut(BaseModel):
    id: UUID
    mode: StudyModeIn
    status: Literal["open", "finished", "cancelled"]
    started_at: datetime
    ended_at: datetime | None
    minutes: int
    summary: str | None
    flashcards_created: int
    skills: list[SkillLevelOut]
    greeting: str
    conversation: ConversationOut
    lesson_ids: list[UUID]
