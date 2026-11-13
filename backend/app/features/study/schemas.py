"""Contrat de la session guidée (SPEC F14, 14.2 ; D103) : départ (bloc du jour ou leçon choisie),
fin ou abandon (`PATCH`, 14.2), état d'une session (écran de fin) et résumé (série, heures de la
semaine, minuteur, bloc du jour)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

StudyModeIn = Literal["socratic", "feynman", "direct"]
# `interrupted` : session encore ouverte en base dont la session d'agents est terminée (échec,
# annulation) ; lue ainsi sans écriture (D91). « Terminer » y enregistre quand même le temps.
StudyStatusOut = Literal["open", "finished", "cancelled", "interrupted"]
TaskTypeOut = Literal["lire", "regarder", "pratiquer", "quiz", "projet"]
SkillLevelValue = Literal["declare", "en_cours", "valide", "prouve"]


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
    # Minuteur du front (travail seul) ; absent : 0. Borné par la durée réelle (D103).
    worked_minutes: int | None = Field(default=None, ge=0, le=600)


class SkillLevelOut(BaseModel):
    name: str
    level: SkillLevelValue


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
    type: TaskTypeOut


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
