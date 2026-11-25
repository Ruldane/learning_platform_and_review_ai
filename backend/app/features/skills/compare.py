"""Comparison of the map with a target (SPEC F15, D107 #2, D123): "target job" = the skills of the
goal's program; "specific offer" = the learnable skills of the offer; expected at level
`valide`. Read-only, outside `service` like `map` (cycle with `program`); the goal is read by
`learning.service`, the program by `program.service`, the offer by `gap.service` (contract 2)."""

from math import floor

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.skills import LEVEL_ORDER, SkillLevel
from app.features.gap.service.links import posting_skills
from app.features.learning.service.goals import get_goal, list_goals
from app.features.program.service.skill_modules import program_skill_names
from app.features.skills.radar import as_level, domain_name
from app.features.skills.repository import SkillRepository, UserSkillRepository
from app.features.skills.schemas import CompareOut, CompareRowOut, CompareTarget

TARGET_LEVEL: SkillLevel = "validated"
LABEL_MAX = 120


def no_compare_target() -> AppError:
    message = "Create a program for a goal before comparing skills."
    return AppError("no_compare_target", message, 404)


def gap(mine: SkillLevel | None, target: SkillLevel) -> int:
    """Rank of the target minus mine (`LEVEL_ORDER`, absent = −1); 0 or less: reached."""
    rank = LEVEL_ORDER.index(mine) if mine is not None else -1
    return LEVEL_ORDER.index(target) - rank


async def _target(db: AsyncSession, user_id: str, goal_id: str | None) -> tuple[str, str]:
    """`(label, program)` of the compared goal: the one requested (404 `goal_not_found` if it is not
    January's), otherwise the most recent one that has a program; 404 `no_compare_target` without a
    program. The label is the target role, otherwise the goal's text."""
    goals = [await get_goal(db, user_id, goal_id)] if goal_id is not None else None
    for goal in goals if goals is not None else await list_goals(db, user_id):
        if goal.program_id is not None:
            label = (goal.target_role or goal.text).strip()[:LABEL_MAX]
            return label, goal.program_id
    raise no_compare_target()


async def _compare(db: AsyncSession, user_id: str, label: str, names: list[str]) -> CompareOut:
    """One row per skill of `names` (normalized names, in their order) present in the reference
    data, target `valide`; `coverage` = share of reached rows, in %, rounded up from 0.5 (0 without
    rows)."""
    found = await SkillRepository(db, user_id).by_norm(names)
    skills = [found[name] for name in names if name in found]
    levels = await UserSkillRepository(db, user_id).for_skills([skill.id for skill in skills])
    rows: list[CompareRowOut] = []
    for skill in skills:
        mine = as_level(levels[skill.id].level) if skill.id in levels else None
        rows.append(
            CompareRowOut(
                skill_id=skill.id,
                name=skill.name,
                domain=domain_name(skill.domain),
                mine=mine,
                target=TARGET_LEVEL,
                gap=gap(mine, TARGET_LEVEL),
            )
        )
    reached = sum(1 for row in rows if row.gap <= 0)
    coverage = floor(100 * reached / len(rows) + 0.5) if rows else 0
    return CompareOut(target_label=label, coverage=coverage, rows=rows)


async def compare_with_goal(db: AsyncSession, user_id: str, goal_id: str | None) -> CompareOut:
    """The skills of the goal's program, in its order (see `_compare`)."""
    label, program_id = await _target(db, user_id, goal_id)
    return await _compare(db, user_id, label, await program_skill_names(db, user_id, program_id))


async def compare_with_posting(db: AsyncSession, user_id: str, posting_id: str) -> CompareOut:
    """Me facing this offer (D123): its learnable skills (name linked to the reference data,
    otherwise that of the need), in the analysis order, expected `valide`; label "Title — Company".
    404 `posting_not_found`, or `no_compare_target` while the offer is not analysed."""
    found = await posting_skills(db, user_id, posting_id)
    if found is None:
        message = "Analyse this posting before comparing skills."
        raise AppError("no_compare_target", message, 404)
    return await _compare(db, user_id, found.label, found.names)


def posting_id_required() -> AppError:
    return AppError(
        "posting_id_required", "Choose the posting to compare.", 422, {"fields": ["posting_id"]}
    )


async def compare_with(
    db: AsyncSession,
    user_id: str,
    target: CompareTarget,
    *,
    goal_id: str | None,
    posting_id: str | None,
) -> CompareOut:
    """The requested comparison; `posting` without `posting_id`: 422 `posting_id_required`."""
    if target == "goal":
        return await compare_with_goal(db, user_id, goal_id)
    if posting_id is None:
        raise posting_id_required()
    return await compare_with_posting(db, user_id, posting_id)
