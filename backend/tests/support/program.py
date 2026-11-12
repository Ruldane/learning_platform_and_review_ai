"""Fabriques de brouillons de programme pour les tests de planification."""

from datetime import date

from app.agents.tools.plan_schema import (
    ModuleDraft,
    PlanDraft,
    SkillDraft,
    TaskDraft,
    WeekDraft,
)
from app.db.models.program import TaskType

MONDAY = date(2026, 11, 16)


def task(title: str, kind: TaskType = "lire", minutes: int = 30) -> TaskDraft:
    return TaskDraft(title=title, type=kind, minutes=minutes, done_criterion="Notes prises")


def module(title: str, tasks: list[TaskDraft], skills: list[str] | None = None) -> ModuleDraft:
    return ModuleDraft(title=title, skills=skills or [title], tasks=tasks)


def week(theme: str, modules: list[ModuleDraft]) -> WeekDraft:
    return WeekDraft(theme=theme, objective="Savoir faire", deliverable="Un dépôt", modules=modules)


def plan(weeks: list[WeekDraft], title: str = "Parcours IA") -> PlanDraft:
    return PlanDraft(title=title, weeks=weeks, skills=[SkillDraft(name="Python", domain="Code")])


def full_week(theme: str, minutes: list[int]) -> WeekDraft:
    """Une semaine d'un module : des lectures, puis la pratique et le quiz de la semaine."""
    tasks = [task(f"Lire le chapitre {i}", minutes=m) for i, m in enumerate(minutes, start=1)]
    tasks += [task(f"Pratiquer {theme}", "pratiquer", 45), task("Faire le quiz", "quiz", 20)]
    return week(theme, [module(f"Module {theme}", tasks)])
