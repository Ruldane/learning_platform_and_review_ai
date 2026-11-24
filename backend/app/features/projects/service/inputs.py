"""Ce que le Praticien lit d'un projet (P1, P2, P4, D166) : l'énoncé d'un module (`BriefInputs`) et
le rendu à évaluer (`ReviewInputs`). Lecture seule, relue à chaque appel : le port n'a pas d'état.
Un module disparu après une replanification rend les compétences vides pour l'évaluation (le
projet reste évaluable) mais empêche d'écrire l'énoncé (404). Jamais journalisé : titres, leçon,
poste et rendu sont des données de l'utilisatrice (17.2)."""

from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.project_port import LESSON_EXCERPT_MAX, BriefInputs, ReviewInputs
from app.agents.tools.project_schema import ProjectBrief
from app.core.errors import AppError
from app.db.models.daily import Project
from app.db.models.program import Module, Week
from app.features.cv.service.versions import validated_profile
from app.features.learning.service.goals import list_goals
from app.features.lessons.service.lessons import ready_markdown
from app.features.program.service.programs import load
from app.features.projects.repository import ProjectRepository
from app.features.projects.service.errors import project_not_found, project_not_ready
from app.features.projects.service.runtime import ProjectsRuntime
from app.features.settings.service import SettingsService


async def owned(db: AsyncSession, user_id: str, project_id: str) -> Project:
    row = await ProjectRepository(db, user_id).get_fresh(project_id)
    if row is None:
        raise project_not_found()
    return row


async def module_of(
    db: AsyncSession, user_id: str, row: Project
) -> tuple[Module, Week | None] | None:
    """Le module du projet et sa semaine, `None` si le module n'existe plus."""
    try:
        loaded = await load(db, user_id, row.program_id)
    except AppError:
        return None
    module = next((item for item in loaded.modules if item.id == row.module_id), None)
    if module is None:
        return None
    return module, next((week for week in loaded.weeks if week.id == module.week_id), None)


async def module_skills(db: AsyncSession, user_id: str, row: Project) -> list[str]:
    found = await module_of(db, user_id, row)
    return [str(skill) for skill in found[0].skills] if found else []


def _language(code: str) -> Literal["fr", "en"]:
    return "en" if code == "en" else "fr"


async def _target_role(db: AsyncSession, user_id: str, configured: str) -> str | None:
    """Le poste visé : celui du radar dans les réglages, sinon celui du dernier objectif."""
    if configured.strip():
        return configured.strip()
    goals = await list_goals(db, user_id)
    return (goals[0].target_role or "").strip() or None if goals else None


async def brief_inputs(rt: ProjectsRuntime, user_id: str, project_id: str) -> BriefInputs:
    async with rt.session_factory() as db:
        row = await owned(db, user_id, project_id)
        found = await module_of(db, user_id, row)
        if found is None:
            raise AppError("module_not_found", "The module for this project no longer exists.", 404)
        module, week = found
        settings = await SettingsService(db, user_id).get()
        excerpt = await ready_markdown(db, user_id, module.id)
        return BriefInputs(
            module_title=module.title,
            skills=[str(skill) for skill in module.skills],
            prerequisites=[str(item) for item in module.prerequisites],
            lesson_excerpt=excerpt[:LESSON_EXCERPT_MAX] if excerpt else None,
            week_deliverable=week.deliverable if week else None,
            role=await _target_role(db, user_id, settings.radar_role),
            language=_language(settings.lesson_language),
        )


def latest_submission(row: Project) -> dict[str, Any]:
    """Le dernier rendu ; vide si le projet n'en a pas."""
    return dict(row.submissions[-1]) if row.submissions else {}


async def review_inputs(rt: ProjectsRuntime, user_id: str, project_id: str) -> ReviewInputs:
    async with rt.session_factory() as db:
        row = await owned(db, user_id, project_id)
        if not row.brief:
            raise project_not_ready()
        submission = latest_submission(row)
        settings = await SettingsService(db, user_id).get()
        return ReviewInputs(
            title=row.title,
            brief=ProjectBrief.model_validate(row.brief),
            repo_url=submission.get("repo_url"),
            description=submission.get("description"),
            screenshots=len(submission.get("screenshots", [])),
            skills=await module_skills(db, user_id, row),
            profile=await validated_profile(db, user_id),
            language=_language(settings.lesson_language),
        )
