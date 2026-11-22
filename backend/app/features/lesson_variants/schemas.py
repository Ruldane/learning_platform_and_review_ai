from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class LessonVariantCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lesson_id: UUID


class LessonVariantSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lesson_id: UUID
    lesson_title: str
    revision: str
    created_at: datetime


class LessonVariantOut(LessonVariantSummary):
    source_markdown: str
    review_markdown: str
    reading_steps: list[str]
