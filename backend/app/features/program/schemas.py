"""Schémas de l'API du programme (SPEC 3.4, 14.2 ; D88) : vue complète (semaines, modules,
tâches, avancement, dernière différence), modifications de January, validation."""

from datetime import date
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.db.models.lessons import LessonStatus
from app.db.models.program import ProgramStatus, TaskStatus, TaskType

# Les types littéraux sont réexportés : un router n'importe pas `app.db` (contrat 1b).
__all__ = [
    "LessonStatus",
    "ModuleOut",
    "MovedTaskOut",
    "PlanDiffOut",
    "ProgramOut",
    "ProgramPatch",
    "ProgramStatus",
    "ProgramSummaryOut",
    "ProgressOut",
    "TaskCreate",
    "TaskOut",
    "TaskPatch",
    "TaskStatus",
    "TaskType",
    "ValidateOut",
    "WeekOut",
]

_Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=120)]
_Criterion = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=200)]
_Id = Annotated[str, Field(min_length=1, max_length=36)]
_Minutes = Annotated[int, Field(ge=15, le=120)]


class TaskOut(BaseModel):
    id: str
    module_id: str
    title: str
    type: TaskType
    minutes: int
    done_criterion: str
    planned_date: date
    status: TaskStatus
    already_known: bool


class ModuleOut(BaseModel):
    id: str
    rank: int
    title: str
    skills: list[str]
    prerequisites: list[str]
    skipped: bool
    lesson_id: str | None
    lesson_status: LessonStatus | None
    resources_count: int
    tasks: list[TaskOut]


class WeekOut(BaseModel):
    """`load_minutes` : tâches planifiées dans les sept jours de la semaine (calendrier)."""

    id: str
    rank: int
    theme: str
    objective: str
    deliverable: str
    start_date: date
    load_minutes: int
    load_hours: float  # arrondi à la demi-heure
    modules: list[ModuleOut]


class ProgressOut(BaseModel):
    done_tasks: int
    total_tasks: int
    done_minutes: int
    total_minutes: int


class MovedTaskOut(BaseModel):
    task: str  # « {module} / {tâche} »
    before: date
    after: date


class PlanDiffOut(BaseModel):
    """Différence de la dernière version du Stratège avec le plan qu'elle a remplacé."""

    added: list[str]
    removed: list[str]
    moved: list[MovedTaskOut]
    weeks_before: int
    weeks_after: int


class ProgramOut(BaseModel):
    id: str
    goal_id: str
    title: str
    status: ProgramStatus
    version: int
    start_date: date
    weekly_minutes: int
    cap_minutes: int
    weekday_minutes: int
    weekend_minutes: int
    session_id: str | None
    weeks: list[WeekOut]
    progress: ProgressOut
    diff: PlanDiffOut | None


class ProgramSummaryOut(BaseModel):
    id: str
    goal_id: str
    title: str
    status: ProgramStatus
    start_date: date
    weeks: int
    progress: ProgressOut


class TaskCreate(BaseModel):
    module_id: _Id
    title: _Title
    type: TaskType
    minutes: _Minutes
    done_criterion: _Criterion
    planned_date: date


class ProgramPatch(BaseModel):
    """Ajouts, suppressions et date de début (un lundi, brouillon seulement), appliqués
    ensemble : une règle cassée annule tout."""

    start_date: date | None = None
    add_tasks: list[TaskCreate] = Field(default_factory=list, max_length=20)
    delete_task_ids: list[_Id] = Field(default_factory=list, max_length=50)


class TaskPatch(BaseModel):
    planned_date: date | None = None
    status: TaskStatus | None = None
    title: _Title | None = None
    minutes: _Minutes | None = None


class ValidateOut(BaseModel):
    """`session_id` : session du Stratège reprise (la validation s'y termine) ; `None` : la
    validation est faite (ou l'était déjà)."""

    program_id: str
    status: ProgramStatus
    session_id: str | None
