"""Programme complet écrit en direct (D213), avec les champs du livre (plan « zéro à expert ») :
étape et raison de chaque semaine, pages officielles, encadré « code ancien » et notions de chaque
chapitre. Tous facultatifs ; donnés, ils suivent les règles du Stratège (`PlanDraft`)."""

from datetime import date
from typing import Annotated, Literal

from pydantic import AnyHttpUrl, BaseModel, Field, StringConstraints

from app.db.models.program import TaskType

_Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=120)]
_Criterion = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=200)]
_Id = Annotated[str, Field(min_length=1, max_length=36)]
_Minutes = Annotated[int, Field(ge=15, le=120)]
_Theme = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=120)]
_Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=300)]
_Skill = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
_Url = Annotated[AnyHttpUrl, Field(max_length=500)]
Url = _Url
Stage = Literal["fondations", "pratique", "avance"]


class TaskWrite(BaseModel):
    """Une tâche d'un programme écrit en direct : les champs et les bornes de `TaskDraft`. Son jour
    est choisi par l'application, comme pour le Stratège."""

    title: _Title
    type: TaskType
    minutes: _Minutes
    done_criterion: _Criterion


class NotionWrite(BaseModel):
    """Une notion introduite par un chapitre, avec sa définition courte."""

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
        description="Notions introduites par un chapitre précédent, dont celui-ci a besoin.",
    )
    introduces: list[NotionWrite] = Field(
        default_factory=list, max_length=10, description="Notions nouvelles de ce chapitre."
    )
    official_urls: list[_Url] = Field(
        default_factory=list, max_length=3, description="Pages de la documentation officielle."
    )
    legacy: list[_Skill] = Field(
        default_factory=list,
        max_length=5,
        description="API dépréciées, montrées seulement dans l'encadré « Lire du code ancien ».",
    )


class WeekWrite(BaseModel):
    theme: _Theme
    objective: _Text
    deliverable: _Text
    stage: Stage | None = Field(
        default=None, description="Étape du livre : les étapes ne reculent jamais."
    )
    rationale: _Text | None = Field(
        default=None, description="Pourquoi cette semaine arrive à cette place."
    )
    modules: list[ModuleWrite] = Field(min_length=1, max_length=4)


class SkillWrite(BaseModel):
    """Une compétence du référentiel, avec son domaine (facultatif : celles des modules sont
    créées sans domaine à la validation)."""

    name: _Skill
    domain: _Skill
    synonyms: list[_Skill] = Field(default_factory=list, max_length=5)


class EdgeWrite(BaseModel):
    """`before` précède `after` (noms de compétences)."""

    before: _Skill
    after: _Skill


class ProgramWrite(BaseModel):
    """Un programme complet écrit en un appel, sans agent (semaines, modules, tâches : les champs
    et les bornes du Stratège, 1 à 52 semaines). L'application range les tâches sur le calendrier
    selon les règles du Stratège ; le programme entre en brouillon, « à valider »."""

    goal_id: _Id
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=200)]
    start_date: date | None = None
    weeks: list[WeekWrite] = Field(min_length=1, max_length=52)
    skills: list[SkillWrite] = Field(default_factory=list, max_length=60)
    edges: list[EdgeWrite] = Field(default_factory=list, max_length=120)
