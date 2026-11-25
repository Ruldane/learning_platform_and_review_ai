"""Program API schemas (SPEC 3.4, 14.2; D88): full view (weeks, modules, tasks, progress, last
difference), January's edits, validation."""

from datetime import date
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, model_validator

from app.db.models.lessons import LessonStatus
from app.db.models.program import ProgramStatus, Stage, TaskStatus, TaskType
from app.features.program.write_schemas import ProgramWrite, TaskWrite, Url, WeekWrite

# The literal types are re-exported: a router does not import `app.db` (contract 1b).
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
    """A task stays in its module (so listed under that module's week) even when January moves
    it to another week: the calendar places it by `planned_date`."""

    id: str
    module_id: str = Field(description="Original module; does not change when the task moves.")
    title: str
    type: TaskType
    minutes: int
    done_criterion: str
    planned_date: date = Field(
        description="Planned day: it is what places the task in a calendar week (load and "
        "rules), not its module."
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
        description="Pages of the chapter's official documentation (3 at most)."
    )
    legacy: list[str] = Field(description='Old APIs to show only in the "Read legacy code" box.')
    tasks: list[TaskOut]


class WeekOut(BaseModel):
    """A week: its load is read from the calendar (tasks whose `planned_date` falls within its
    seven days), its modules are those the Strategist placed in it. After a move, the sum of
    the tasks of `modules` may therefore differ from `load_minutes`."""

    id: str
    rank: int
    theme: str
    objective: str
    deliverable: str
    start_date: date
    stage: Stage | None = Field(description="Stage in the book, if the Strategist provided it.")
    rationale: str | None = Field(
        description="Why the Strategist placed the week at this point in the program."
    )
    load_minutes: int = Field(
        description="Minutes of the tasks planned from Monday to Sunday of this week, "
        "whatever their module (85% rule)."
    )
    load_hours: float = Field(description="`load_minutes` in hours, to the half hour.")
    modules: list[ModuleOut] = Field(
        description="Modules placed in this week, with ALL their tasks, including those "
        "January moved to another week (see `TaskOut.planned_date`)."
    )


class ProgressOut(BaseModel):
    done_tasks: int
    total_tasks: int
    done_minutes: int
    total_minutes: int


class MovedTaskOut(BaseModel):
    task: str  # "{module} / {task}"
    before: date
    after: date


class PlanDiffOut(BaseModel):
    """Difference of the last version (the Strategist's, or "January's edits" written at
    validation) with the plan it replaced."""

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
    """Additions, removals and start date (a Monday, draft only), applied together: a broken
    rule cancels everything."""

    start_date: date | None = None
    add_tasks: list[TaskCreate] = Field(default_factory=list, max_length=20)
    delete_task_ids: list[_Id] = Field(default_factory=list, max_length=50)


class TaskPatch(BaseModel):
    planned_date: date | None = None
    status: TaskStatus | None = None
    title: _Title | None = None
    minutes: _Minutes | None = None


class ValidateOut(BaseModel):
    """`session_id`: the resumed Strategist session (the validation ends there); `None`: the
    validation is done (or already was)."""

    program_id: str
    status: ProgramStatus
    session_id: str | None


class WeekCreate(BaseModel):
    """One more week at the end of the program (52 at most), written by hand or by Claude: it
    has no module or task, they are added afterwards."""

    theme: _Theme
    objective: _Text
    deliverable: _Text


class WeekPatch(BaseModel):
    theme: _Theme | None = None
    objective: _Text | None = None
    deliverable: _Text | None = None
    stage: Stage | None = Field(default=None, description="Stage in the book.")
    rationale: _Text | None = Field(
        default=None, description="Why this week comes at this position."
    )

    @model_validator(mode="after")
    def _something(self) -> "WeekPatch":
        if not self.model_dump(exclude_none=True):
            raise ValueError("nothing to change")
        return self


class ModuleCreate(BaseModel):
    """One more module in a week (4 at most per week), without a task: they are added through
    `PATCH /programs/{id}` (`add_tasks`)."""

    week_id: _Id
    title: _Title
    skills: list[_Skill] = Field(min_length=1, max_length=8)
    prerequisites: list[_Skill] = Field(default_factory=list, max_length=8)


class ModulePatch(BaseModel):
    title: _Title | None = None
    skills: list[_Skill] | None = Field(default=None, min_length=1, max_length=8)
    prerequisites: list[_Skill] | None = Field(default=None, max_length=8)
    official_urls: list[Url] | None = Field(
        default=None, max_length=3, description="Pages of the official documentation."
    )
    legacy: list[_Skill] | None = Field(
        default=None,
        max_length=5,
        description='Deprecated APIs, shown only in the "Read legacy code" box.',
    )

    @model_validator(mode="after")
    def _something(self) -> "ModulePatch":
        if not self.model_dump(exclude_none=True):
            raise ValueError("nothing to change")
        return self
