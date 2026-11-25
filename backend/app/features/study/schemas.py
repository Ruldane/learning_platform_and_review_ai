"""Contract of the guided session (SPEC F14, 14.2; D103): start (the day's block or a chosen
lesson), end or abandonment (`PATCH`, 14.2), state of a session (end screen) and summary (streak,
hours of the week, timer, day's block)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.db.models.program import TaskType
from app.db.models.skills import SkillLevel

StudyModeIn = Literal["socratic", "feynman", "direct"]
# `interrupted`: session still open in the database whose agent session has ended (failure,
# cancellation); read this way without any write (D91). « Terminer » still records the time.
StudyStatusOut = Literal["open", "finished", "cancelled", "interrupted"]


class StudyStart(BaseModel):
    lesson_id: str | None = Field(default=None, min_length=1, max_length=36)
    mode: StudyModeIn = "socratic"
    question: str | None = Field(default=None, max_length=2000)


class StudyStarted(BaseModel):
    study_session_id: str
    session_id: str
    lesson_id: str


class StudyUpdate(BaseModel):
    action: Literal["finish", "cancel"]
    # Front timer (work only); absent: 0. Capped by the real duration (D103).
    worked_minutes: int | None = Field(default=None, ge=0, le=600)


class SkillLevelOut(BaseModel):
    name: str
    level: SkillLevel


class StudySessionOut(BaseModel):
    id: str
    lesson_id: str
    lesson_title: str
    module_title: str
    mode: StudyModeIn
    status: StudyStatusOut
    session_id: str | None
    started_at: datetime
    ended_at: datetime | None
    minutes: int
    summary: str | None
    tasks_done: list[str]
    flashcards_created: int
    skills: list[SkillLevelOut]


class BlockTaskOut(BaseModel):
    id: str
    title: str
    minutes: int
    type: TaskType


class BlockOut(BaseModel):
    lesson_id: str
    lesson_title: str
    module_title: str
    tasks: list[BlockTaskOut]


class StudySummaryOut(BaseModel):
    streak_days: int
    week_minutes: int
    work_minutes: int
    break_minutes: int
    open_session_id: str | None
    block: BlockOut | None
