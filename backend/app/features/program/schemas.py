"""Schémas de l'API du programme (SPEC 3.4, 14.2 ; D88) : vue complète (semaines, modules,
tâches, avancement, dernière différence), modifications de January, validation."""

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, model_validator

from app.db.models.lessons import LessonStatus
from app.db.models.program import ProgramStatus, TaskStatus, TaskType
from app.features.program.write_schemas import ProgramWrite, Stage, TaskWrite, Url, WeekWrite

# Les types littéraux sont réexportés : un router n'importe pas `app.db` (contrat 1b).
__all__ = [
    "LessonStatus",
    "ModuleCreate",
    "ModuleOut",
    "ModulePatch",
    "MovedTaskOut",
    "PlanDiffOut",
    "ProgramOut",
    "ProgramPatch",
    "ProgramStatus",
    "ProgramSummaryOut",
    "ProgramWrite",
    "ProgressOut",
    "TaskCreate",
    "TaskOut",
    "TaskPatch",
    "TaskStatus",
    "TaskType",
    "TaskWrite",
    "ValidateOut",
    "WeekCreate",
    "WeekOut",
    "WeekPatch",
    "WeekWrite",
]

_Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=120)]
_Criterion = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=200)]
_Id = Annotated[str, Field(min_length=1, max_length=36)]
_Minutes = Annotated[int, Field(ge=15, le=120)]
_Theme = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=120)]
_Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=300)]
_Skill = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]


class TaskOut(BaseModel):
    """Une tâche reste dans son module (donc listée sous la semaine de ce module) même quand
    January la déplace dans une autre semaine : le calendrier la place par `planned_date`."""

    id: str
    module_id: str = Field(description="Module d'origine ; ne change pas quand la tâche bouge.")
    title: str
    type: TaskType
    minutes: int
    done_criterion: str
    planned_date: date = Field(
        description="Jour planifié : c'est lui qui range la tâche dans une semaine du "
        "calendrier (charge et règles), pas son module."
    )
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
    official_urls: list[str] = Field(
        description="Pages de la documentation officielle du chapitre (3 au plus)."
    )
    legacy: list[str] = Field(
        description="API anciennes à ne montrer que dans l'encadré « Lire du code ancien »."
    )
    tasks: list[TaskOut]


class WeekOut(BaseModel):
    """Une semaine : sa charge se lit sur le calendrier (tâches dont `planned_date` tombe dans
    ses sept jours), ses modules sont ceux que le Stratège y a rangés. Après un déplacement, la
    somme des tâches de `modules` peut donc différer de `load_minutes`."""

    id: str
    rank: int
    theme: str
    objective: str
    deliverable: str
    start_date: date
    stage: Literal["fondations", "pratique", "avance"] | None = Field(
        description="Étape du livre (fondations, pratique courante, avancé), si le Stratège l'a "
        "donnée."
    )
    rationale: str | None = Field(
        description="Pourquoi cette semaine arrive à cette place, si le Stratège l'a donnée."
    )
    load_minutes: int = Field(
        description="Minutes des tâches planifiées du lundi au dimanche de cette semaine, "
        "quel que soit leur module (règle des 85 %)."
    )
    load_hours: float = Field(description="`load_minutes` en heures, à la demi-heure.")
    modules: list[ModuleOut] = Field(
        description="Modules rangés dans cette semaine, avec TOUTES leurs tâches, y compris "
        "celles que January a déplacées dans une autre semaine (voir `TaskOut.planned_date`)."
    )


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
    """Différence de la dernière version (du Stratège, ou « Modifications de January » écrite à
    la validation) avec le plan qu'elle a remplacé."""

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


class WeekCreate(BaseModel):
    """Une semaine de plus à la fin du programme (52 au plus), écrite à la main ou par Claude :
    elle n'a ni module ni tâche, ils s'ajoutent ensuite."""

    theme: _Theme
    objective: _Text
    deliverable: _Text


class WeekPatch(BaseModel):
    theme: _Theme | None = None
    objective: _Text | None = None
    deliverable: _Text | None = None
    stage: Stage | None = Field(default=None, description="Étape du livre.")
    rationale: _Text | None = Field(
        default=None, description="Pourquoi cette semaine arrive à cette place."
    )

    @model_validator(mode="after")
    def _something(self) -> "WeekPatch":
        if not self.model_dump(exclude_none=True):
            raise ValueError("rien à changer")
        return self


class ModuleCreate(BaseModel):
    """Un module de plus dans une semaine (4 au plus par semaine), sans tâche : elles s'ajoutent
    par `PATCH /programs/{id}` (`add_tasks`)."""

    week_id: _Id
    title: _Title
    skills: list[_Skill] = Field(min_length=1, max_length=8)
    prerequisites: list[_Skill] = Field(default_factory=list, max_length=8)


class ModulePatch(BaseModel):
    title: _Title | None = None
    skills: list[_Skill] | None = Field(default=None, min_length=1, max_length=8)
    prerequisites: list[_Skill] | None = Field(default=None, max_length=8)
    official_urls: list[Url] | None = Field(
        default=None, max_length=3, description="Pages de la documentation officielle."
    )
    legacy: list[_Skill] | None = Field(
        default=None,
        max_length=5,
        description="API dépréciées, montrées seulement dans l'encadré « Lire du code ancien ».",
    )

    @model_validator(mode="after")
    def _something(self) -> "ModulePatch":
        if not self.model_dump(exclude_none=True):
            raise ValueError("rien à changer")
        return self
