from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class StudyReturnReminder(BaseModel):
    model_config = ConfigDict(extra="forbid")

    day: date | None


class StudyReturnSkill(BaseModel):
    id: str
    name: str
    level: Literal["validated", "proven"]


class StudyReturnCard(BaseModel):
    id: str
    front: str
    skill: str | None
    due_date: date


class StudyReturnLastBlock(BaseModel):
    id: str
    kind: Literal["guided", "training"]
    title: str | None
    minutes: int
    ended_at: datetime


class StudyReturnSelection(BaseModel):
    minutes: int
    skills: list[StudyReturnSkill]
    cards: list[StudyReturnCard]
    last_block: StudyReturnLastBlock | None


class StudyReturnPlan(StudyReturnSelection):
    id: str
    prepared_at: datetime
    training_id: str | None


class StudyReturnOut(BaseModel):
    plan: StudyReturnPlan | None
    reminder_on: date | None
    reminder_due: bool
