"""A complete program written directly (phase 10, D213): Claude (through MCP) gives the goal,
the title, the start date and the weeks, modules and tasks; the application stores them as the
Strategist's port does (`AgentProgramStore.save_draft`: same bounds, same `check_draft` and
`schedule` rules, same rows, a "pending" version), without an agent, a session or a model call.
The program enters as a draft, "to validate"; the validation stays the same
(`POST /programs/{id}/validate`, level 3 for MCP).

Everything is written by the ORM in a single transaction: undoing from the history removes the
program, its weeks, its modules, its tasks and its version. Under the goal's lock (key of the
programs lock): a goal has only one program (409 `program_exists`)."""

import logging
from datetime import date

from pydantic import ValidationError
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

REASON = "Program written directly, without an agent."
DEFAULT_DOMAIN = "Other"  # the displayed domain of a skill without a domain (skills radar)
MAX_SKILLS = 60  # the Strategist's reference list (`PlanDraft.skills`)


def program_exists() -> AppError:
    return AppError(
        "program_exists",
        "This goal already has a program. Edit it using PATCH /programs/{id}.",
        409,
    )


def plan_invalid(problems: list[str]) -> AppError:
    return AppError(
        "plan_invalid",
        "The program does not meet the scheduling rules. Correct it and submit it again.",
        422,
        {"problems": problems},
    )


def _draft_of(body: ProgramWrite) -> PlanDraft:
    """The Strategist's draft: without a given reference list, the one of the modules' skills."""
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
    try:
        return PlanDraft.model_validate(data)
    except (
        ValidationError
    ) as exc:  # the order of the notions: messages without the received value (D303)
        raise plan_invalid([str(error["msg"]) for error in exc.errors()]) from None


async def write_program(rt: ProgramRuntime, user_id: str, body: ProgramWrite) -> ProgramOut:
    """See the module: 404 `goal_not_found` (another user's goal included), 409 `program_exists`,
    422 `invalid_start_date`, `planning_impossible`, `plan_invalid` (the problems, in sentences)."""
    check_start_date(body.start_date)
    async with rt.program_lock(user_id, body.goal_id), rt.session_factory() as db:
        goal = await owned_goal(db, user_id, body.goal_id)
        if (await program_of(db, user_id, goal.id))[0] is not None:
            raise program_exists()
        program_id = await _write(db, user_id, goal.weekly_minutes, body)
        await db.commit()
        out = await get_program(db, user_id, program_id)
    logger.info("Program written directly: goal %s, program %s", body.goal_id, program_id)
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
