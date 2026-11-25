"""A complete program written directly (D213), with the book's fields ("zero to expert" plan):
stage and reason of each week, official pages, "legacy code" box and notions of each chapter.
All optional; when given, they follow the Strategist's rules (`PlanDraft`)."""

from datetime import date
from typing import Annotated

from pydantic import AnyHttpUrl, BaseModel, Field, StringConstraints

from app.db.models.program import Stage, TaskType

_Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=120)]
_Criterion = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=200)]
_Id = Annotated[str, Field(min_length=1, max_length=36)]
_Minutes = Annotated[int, Field(ge=15, le=120)]
_Theme = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=120)]
_Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=300)]
_Skill = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
_Url = Annotated[AnyHttpUrl, Field(max_length=500)]
Url = _Url


class TaskWrite(BaseModel):
    """A task of a program written directly: the fields and bounds of `TaskDraft`. Its day is
    chosen by the application, like for the Strategist."""

    title: _Title
    type: TaskType
    minutes: _Minutes
    done_criterion: _Criterion


class NotionWrite(BaseModel):
    """A notion introduced by a chapter, with its short definition."""

    name: _Skill
    definition: _Text


class ModuleWrite(BaseModel):
    title: _Title
    skills: list[_Skill] = Field(min_length=1, max_length=8)
    prerequisites: list[_Skill] = Field(default_factory=list, max_length=8)
    tasks: list[TaskWrite] = Field(min_length=1, max_length=12)
    requires: list[_Skill] = Field(
        default_factory=list,
        max_length=10,
        description="Notions introduced by a previous chapter, which this one needs.",
    )
    introduces: list[NotionWrite] = Field(
        default_factory=list, max_length=10, description="Notions nouvelles de ce chapitre."
    )
    official_urls: list[_Url] = Field(
        default_factory=list, max_length=3, description="Pages of the official documentation."
    )
    legacy: list[_Skill] = Field(
        default_factory=list,
        max_length=5,
        description='Deprecated APIs, shown only in the "Read legacy code" box.',
    )


class WeekWrite(BaseModel):
    theme: _Theme
    objective: _Text
    deliverable: _Text
    stage: Stage | None = Field(
        default=None, description="Stage in the book. Weeks follow the stages in order."
    )
    rationale: _Text | None = Field(
        default=None, description="Why the week appears at this point in the program."
    )
    modules: list[ModuleWrite] = Field(min_length=1, max_length=4)


class SkillWrite(BaseModel):
    """A skill of the reference list, with its domain (optional: those of the modules are
    created without a domain at validation)."""

    name: _Skill
    domain: _Skill
    synonyms: list[_Skill] = Field(default_factory=list, max_length=5)


class EdgeWrite(BaseModel):
    """`before` precedes `after` (skill names)."""

    before: _Skill
    after: _Skill


class ProgramWrite(BaseModel):
    """A complete program written in one call, without an agent (weeks, modules, tasks: the
    Strategist's fields and bounds, 1 to 52 weeks). The application places the tasks on the
    calendar following the Strategist's rules; the program enters as a draft, "to validate"."""

    goal_id: _Id
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=200)]
    start_date: date | None = None
    weeks: list[WeekWrite] = Field(min_length=1, max_length=52)
    skills: list[SkillWrite] = Field(default_factory=list, max_length=60)
    edges: list[EdgeWrite] = Field(default_factory=list, max_length=120)
