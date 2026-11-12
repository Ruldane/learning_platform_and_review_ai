"""Sortie structurée du Stratège : le programme avant ordonnancement (SPEC 3.4).

Les bornes sont celles des règles du programme : une tâche dure de 15 à 120 minutes, une
semaine compte 1 à 4 modules, un programme 1 à 52 semaines. Le moteur n'importe aucune feature
(contrat 6) : le calendrier (`features.program.service`) consomme ces types.
"""

from collections.abc import Mapping

from pydantic import BaseModel, Field

from app.agents.runtime.prose import Prose
from app.db.models.program import TaskType
from app.db.models.skills import SkillLevel

# Compétences déjà connues de January : clé = `normalize_skill_name`, valeur = niveau.
KnownSkills = Mapping[str, SkillLevel]


class TaskDraft(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    type: TaskType
    minutes: int = Field(ge=15, le=120)
    done_criterion: Prose = Field(min_length=3, max_length=200)


class ModuleDraft(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    skills: list[str] = Field(min_length=1, max_length=8)
    prerequisites: list[str] = Field(default_factory=list, max_length=8)
    tasks: list[TaskDraft] = Field(min_length=1, max_length=12)


class WeekDraft(BaseModel):
    theme: str = Field(min_length=3, max_length=120)
    objective: Prose = Field(min_length=3, max_length=300)
    deliverable: Prose = Field(min_length=3, max_length=300)
    modules: list[ModuleDraft] = Field(min_length=1, max_length=4)


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
