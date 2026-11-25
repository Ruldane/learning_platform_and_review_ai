"""Structured output of the Strategist: the program before scheduling (SPEC 3.4).

The bounds are those of the program rules: a task lasts 15 to 120 minutes, a week has 1 to 4
modules, a program 1 to 52 weeks. The engine imports no feature (contract 6): the calendar
(`features.program.service`) consumes these types.
"""

from collections.abc import Mapping
from typing import Annotated, Self
from urllib.parse import urlsplit

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    Field,
    PrivateAttr,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.agents.runtime.prose import Prose, ShortenToMax
from app.core.skills import normalize_skill_name
from app.db.models.program import Stage, TaskType
from app.db.models.skills import SkillLevel

# Skills January already knows: key = `normalize_skill_name`, value = level.
KnownSkills = Mapping[str, SkillLevel]
NotionName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
_LEGACY_STAGES = {"fondations": "foundations", "pratique": "practice", "avance": "advanced"}
_LEGACY_TASK_TYPES = {
    "lire": "read",
    "regarder": "watch",
    "pratiquer": "practice",
    "projet": "project",
}
MAX_OFFICIAL_URLS = 3
MAX_LEGACY = 5


def _http_url(value: str) -> str:
    """An http(s) address with a host; the message never names the received value (D303)."""
    parts = urlsplit(value.strip())
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError("An official page must have an http or https address.")
    return value.strip()


OfficialUrl = Annotated[str, StringConstraints(max_length=500), AfterValidator(_http_url)]
Rationale = Annotated[str, Field(min_length=3, max_length=300), ShortenToMax()]
LegacyName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]


def read_checkpoint_task_type(value: object) -> object:
    return _LEGACY_TASK_TYPES.get(value, value) if isinstance(value, str) else value


CheckpointTaskType = Annotated[TaskType, BeforeValidator(read_checkpoint_task_type)]


class TaskDraft(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    type: CheckpointTaskType
    minutes: int = Field(ge=15, le=120)
    done_criterion: Prose = Field(min_length=3, max_length=200)


class NotionDraft(BaseModel):
    name: NotionName
    definition: Prose = Field(min_length=3, max_length=300)


class ChapterOutline(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    requires: list[NotionName] = Field(default_factory=list, max_length=10)
    introduces: list[NotionDraft] = Field(default_factory=list, max_length=10)


class ModuleDraft(ChapterOutline):
    skills: list[str] = Field(min_length=1, max_length=8)
    prerequisites: list[str] = Field(default_factory=list, max_length=8)
    tasks: list[TaskDraft] = Field(min_length=1, max_length=12)
    # Pages of the chapter's official documentation, and deprecated or secondary APIs
    # to show only in the "Reading legacy code" box (mandatory for the Strategist).
    official_urls: list[OfficialUrl] = Field(default_factory=list, max_length=MAX_OFFICIAL_URLS)
    legacy: list[LegacyName] = Field(default_factory=list, max_length=MAX_LEGACY)
    _chapter_index: int | None = PrivateAttr(default=None)

    @property
    def chapter_index(self) -> int | None:
        return self._chapter_index

    def with_chapter_index(self, index: int) -> Self:
        copy = self.model_copy()
        copy._chapter_index = index
        return copy


class WeekDraft(BaseModel):
    theme: str = Field(min_length=3, max_length=120)
    objective: Prose = Field(min_length=3, max_length=300)
    deliverable: Prose = Field(min_length=3, max_length=300)
    # Stage of the book and reason for this place: optional here (direct write, MCP),
    # mandatory for the Strategist.
    stage: Stage | None = None
    rationale: Rationale | None = None
    modules: list[ModuleDraft] = Field(min_length=1, max_length=4)

    @field_validator("stage", mode="before")
    @classmethod
    def read_checkpoint_stage(cls, value: object) -> object:
        return _LEGACY_STAGES.get(value, value) if isinstance(value, str) else value


class SkillDraft(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    domain: str = Field(min_length=2, max_length=120)
    synonyms: list[str] = Field(default_factory=list, max_length=5)


class EdgeDraft(BaseModel):
    """`before` comes before `after` (skill names)."""

    before: str
    after: str


class PlanDraft(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    weeks: list[WeekDraft] = Field(min_length=1, max_length=52)
    skills: list[SkillDraft] = Field(min_length=1, max_length=60)
    edges: list[EdgeDraft] = Field(default_factory=list, max_length=120)

    def with_chapter_indices(self) -> Self:
        if not any(m.requires or m.introduces for week in self.weeks for m in week.modules):
            return self
        weeks: list[WeekDraft] = []
        index = 0
        for week in self.weeks:
            modules = [m.with_chapter_index(index + n) for n, m in enumerate(week.modules)]
            weeks.append(week.model_copy(update={"modules": modules}))
            index += len(modules)
        return self.model_copy(update={"weeks": weeks})

    @model_validator(mode="after")
    def check_chapter_order(self) -> Self:
        chapters = [module for week in self.weeks for module in week.modules]
        introduced: set[str] = set()
        for rank, chapter in enumerate(chapters, start=1):
            for index, name in enumerate(chapter.requires, start=1):
                if normalize_skill_name(name) not in introduced:
                    raise ValueError(
                        f"Chapter {rank} requires a notion (position {index}) "
                        "that must be introduced in an earlier chapter."
                    )
            for index, notion in enumerate(chapter.introduces, start=1):
                normalized = normalize_skill_name(notion.name)
                if not normalized or normalized in introduced:
                    raise ValueError(
                        f"Chapter {rank} must introduce a new notion "
                        f"with a distinct name (position {index})."
                    )
                introduced.add(normalized)
        return self
