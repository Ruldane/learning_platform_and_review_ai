"""Sortie structurée du Stratège : le programme avant ordonnancement (SPEC 3.4).

Les bornes sont celles des règles du programme : une tâche dure de 15 à 120 minutes, une
semaine compte 1 à 4 modules, un programme 1 à 52 semaines. Le moteur n'importe aucune feature
(contrat 6) : le calendrier (`features.program.service`) consomme ces types.
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

# Compétences déjà connues de January : clé = `normalize_skill_name`, valeur = niveau.
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
    """Adresse http(s) avec un hôte ; le message ne nomme jamais la valeur reçue (D303)."""
    parts = urlsplit(value.strip())
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError("Une page officielle doit avoir une adresse http ou https.")
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
    # Pages de la documentation officielle du chapitre, et API dépréciées ou devenues secondaires
    # à ne montrer que dans l'encadré « Lire du code ancien » (obligatoires pour le Stratège).
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
    # Étape du livre et raison de cette place : facultatives ici (écriture directe, MCP),
    # obligatoires pour le Stratège.
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
    """`before` précède `after` (noms de compétences)."""

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
                        f"Le chapitre {rank} requiert une notion (position {index}) "
                        "qui doit être introduite dans un chapitre précédent."
                    )
            for index, notion in enumerate(chapter.introduces, start=1):
                normalized = normalize_skill_name(notion.name)
                if not normalized or normalized in introduced:
                    raise ValueError(
                        f"Le chapitre {rank} doit introduire une notion nouvelle "
                        f"avec un nom distinct (position {index})."
                    )
                introduced.add(normalized)
        return self
