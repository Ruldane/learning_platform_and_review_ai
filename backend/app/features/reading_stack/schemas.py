from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.db.models.reading_stack import ReadingKind, SourceKind

__all__ = [
    "ReadingDetail",
    "ReadingItemOut",
    "ReadingKind",
    "ReadingPage",
    "ReadState",
    "ReadingSourceIn",
    "ReadingSourceOut",
    "ReadingSourceState",
]

Label = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Value = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class ReadingItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    kind: ReadingKind
    title: str
    url: str
    summary: str
    reason: str
    company: str | None
    read_at: datetime | None
    created_at: datetime


class ReadingDetail(ReadingItemOut):
    text: str


class ReadingPage(BaseModel):
    items: list[ReadingItemOut]
    unread_count: int
    next_offset: int | None


class ReadState(BaseModel):
    read: bool


class ReadingSourceIn(BaseModel):
    kind: SourceKind
    label: Label
    value: Value


class ReadingSourceOut(ReadingSourceIn):
    model_config = ConfigDict(from_attributes=True)

    id: str
    active: bool


class ReadingSourceState(BaseModel):
    active: bool


class PlanReadingIn(BaseModel):
    program_id: str = Field(min_length=1, max_length=36)


class ReadingApplicationIn(BaseModel):
    company: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    distinct_from: list[str] = Field(default_factory=list, max_length=10)


class MemorySaved(BaseModel):
    memory_item_id: str


class CardsSaved(BaseModel):
    count: int


class ReadingPlanStarted(BaseModel):
    session_id: str


class ReadingApplicationSaved(BaseModel):
    application_id: str
