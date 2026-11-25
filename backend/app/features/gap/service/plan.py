""" "Add to the plan" from a posting's gap (SPEC F8, D123): the ticked lines feed a replanning
proposal for the chosen validated program, the most recent by default. A 422 gives the faulty
rank, and the logs keep ids and numbers."""

import logging
from collections.abc import Sequence

from app.core.errors import AppError
from app.core.skills import normalize_skill_name
from app.features.gap.service.rows import gap_rows
from app.features.gap.service.score import GapRow
from app.features.postings.service.queries import get_posting
from app.features.program.service.replan_gap import latest_validated
from app.features.replan.service.launch import start_gap_replan
from app.features.replan.service.runtime import ReplanRuntime

logger = logging.getLogger(__name__)


def gap_skill_unknown(fields: list[str], *, allow_out_of_scope: bool) -> AppError:
    sections = '"To add" or "Out of scope"' if allow_out_of_scope else '"To add"'
    return AppError(
        "gap_skill_unknown",
        f"Select a skill listed under {sections} in this posting's gap analysis.",
        422,
        {"fields": fields},
    )


def no_program() -> AppError:
    return AppError(
        "no_program", "Create and approve a program before adding skills to your schedule.", 409
    )


def chosen_skills(
    rows: Sequence[GapRow], skills: Sequence[str], *, allow_out_of_scope: bool = False
) -> list[str]:
    """The canonical names of the ticked lines, without duplicates, in the request's order."""
    allowed = {"to_add", "out_of_scope"} if allow_out_of_scope else {"to_add"}
    to_add = {normalize_skill_name(r.skill): r.skill for r in rows if r.action in allowed}
    names: list[str] = []
    fields: list[str] = []
    for index, skill in enumerate(skills):
        name = to_add.get(normalize_skill_name(skill))
        if name is None:
            fields.append(f"skills.{index}")
        elif name not in names:
            names.append(name)
    if fields:
        raise gap_skill_unknown(fields, allow_out_of_scope=allow_out_of_scope)
    return names


async def plan_gap(
    rt: ReplanRuntime,
    user_id: str,
    posting_id: str,
    skills: Sequence[str],
    *,
    program_id: str | None = None,
) -> str:
    """Launches a proposal in a validated program belonging to the user."""
    async with rt.session_factory() as db:
        posting = await get_posting(db, user_id, posting_id)
        names = chosen_skills(await gap_rows(db, user_id, posting), skills, allow_out_of_scope=True)
        target = program_id if program_id is not None else await latest_validated(db, user_id)
    if target is None:
        raise no_program()
    session_id = await start_gap_replan(rt, user_id, target, names)
    logger.info(
        "Added to the plan: user %s, posting %s, program %s, %d skill(s), session %s",
        user_id,
        posting_id,
        target,
        len(names),
        session_id,
    )
    return session_id
