"""Programme complet écrit en direct (phase 10, D213) : Claude (par le MCP) donne l'objectif, le
titre, la date de début et les semaines, modules et tâches ; l'application les range comme le fait
le port du Stratège (`AgentProgramStore.save_draft` : mêmes bornes, mêmes règles `check_draft` et
`schedule`, mêmes lignes, une version « en attente »), sans agent, sans session et sans appel au
modèle. Le programme entre en brouillon, « à valider » ; la validation reste la même
(`POST /programs/{id}/validate`, niveau 3 pour le MCP).

Tout est écrit par l'ORM dans une seule transaction : l'annulation de l'historique retire le
programme, ses semaines, ses modules, ses tâches et sa version. Sous le verrou de l'objectif (clé
du verrou des programmes) : un objectif n'a qu'un programme (409 `program_exists`)."""

import logging
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.plan_schema import PlanDraft
from app.core.errors import AppError
from app.features.learning.service.choice import check_start_date
from app.features.learning.service.goals import owned_goal, program_of
from app.features.program.repository import PlanVersionRepository, ProgramRepository
from app.features.program.schemas import ProgramOut, ProgramWrite
from app.features.program.service.diff import diff_plans
from app.features.program.service.drafting import (
    budget_of,
    known_skills,
    nothing_to_plan,
    plan_snapshot,
    write_rows,
)
from app.features.program.service.planning import (
    PRACTICE_MINUTES,
    QUIZ_MINUTES,
    PlanningImpossible,
    check_draft,
    next_monday,
    schedule,
)
from app.features.program.service.programs import get_program
from app.features.program.service.runtime import ProgramRuntime

logger = logging.getLogger(__name__)

REASON = "Programme écrit directement, sans agent."
DEFAULT_DOMAIN = (
    "Autres"  # le domaine affiché d'une compétence sans domaine (radar des compétences)
)
MAX_SKILLS = 60  # le référentiel du Stratège (`PlanDraft.skills`)


def program_exists() -> AppError:
    return AppError(
        "program_exists",
        "Cet objectif a déjà un programme : retouche-le (PATCH /programs/{id}, semaines, modules).",
        409,
    )


def plan_invalid(problems: list[str]) -> AppError:
    return AppError(
        "plan_invalid",
        "Le programme ne respecte pas les règles du calendrier : corrige-le et renvoie-le.",
        422,
        {"problems": problems},
    )


def _draft_of(body: ProgramWrite) -> PlanDraft:
    """Le brouillon du Stratège : sans référentiel donné, celui des compétences des modules."""
    data = body.model_dump(mode="json", exclude={"goal_id", "start_date"})
    if not data["skills"]:
        names = dict.fromkeys(
            skill
            for week in data["weeks"]
            for module in week["modules"]
            for skill in module["skills"]
        )
        data["skills"] = [
            {"name": name, "domain": DEFAULT_DOMAIN} for name in list(names)[:MAX_SKILLS]
        ]
    return PlanDraft.model_validate(data)


async def write_program(rt: ProgramRuntime, user_id: str, body: ProgramWrite) -> ProgramOut:
    """Voir le module : 404 `goal_not_found` (objectif d'une autre compris), 409 `program_exists`,
    422 `invalid_start_date`, `planning_impossible`, `plan_invalid` (les problèmes, en phrases)."""
    check_start_date(body.start_date)
    async with rt.program_lock(user_id, body.goal_id), rt.session_factory() as db:
        goal = await owned_goal(db, user_id, body.goal_id)
        if (await program_of(db, user_id, goal.id))[0] is not None:
            raise program_exists()
        program_id = await _write(db, user_id, goal.weekly_minutes, body)
        await db.commit()
        out = await get_program(db, user_id, program_id)
    logger.info("Programme écrit en direct : objectif %s, programme %s", body.goal_id, program_id)
    return out


async def _write(db: AsyncSession, user_id: str, weekly: int | None, body: ProgramWrite) -> str:
    budget = await budget_of(db, user_id, weekly)
    if budget.cap_minutes < PRACTICE_MINUTES + QUIZ_MINUTES:
        raise PlanningImpossible()
    draft = _draft_of(body)
    if problems := check_draft(draft, budget):
        raise plan_invalid(problems)
    start: date = body.start_date or next_monday(date.today())
    plan = schedule(draft, budget, await known_skills(db, user_id), start)
    if not plan.weeks:
        raise nothing_to_plan()
    program = await ProgramRepository(db, user_id).add(
        goal_id=body.goal_id,
        title=draft.title,
        version=0,
        status="draft",
        start_date=start,
        weekly_minutes=budget.weekly_minutes,
        cap_minutes=budget.cap_minutes,
        session_id=None,
    )
    chapter_indices = await write_rows(db, user_id, program.id, plan, draft)
    after = plan_snapshot(plan, draft, budget, chapter_indices)
    versions = PlanVersionRepository(db, user_id)
    program.version = await versions.next_version(program.id)
    await versions.add(
        program_id=program.id,
        version=program.version,
        snapshot=after,
        diff=diff_plans(None, after).to_json(),
        reason=REASON,
    )
    await db.flush()
    return program.id
