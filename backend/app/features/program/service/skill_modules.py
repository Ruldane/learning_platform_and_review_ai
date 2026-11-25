"""Skills seen from the modules (read for the skill map, D107): the module that teaches a skill
(next action) and the skills of a program (target of the comparison). Names are compared
normalized (`normalize_skill_name`)."""

from collections.abc import AsyncIterator
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.replan_port import GAP_MODULE_TITLES
from app.core.skills import normalize_skill_name
from app.db.models.program import Module
from app.features.program.repository import ProgramRepository
from app.features.program.service.programs import load


@dataclass(frozen=True)
class SkillModule:
    module_id: str
    program_id: str
    title: str


@dataclass(frozen=True)
class SkillCoverage:
    weeks: dict[str, int]
    offer_weeks: dict[str, int]


def _norms(module: Module) -> list[str]:
    return [norm for norm in (normalize_skill_name(str(s)) for s in module.skills) if norm]


async def module_teaching(db: AsyncSession, user_id: str, norm_name: str) -> SkillModule | None:
    """The first non-skipped module that teaches the skill (normalized name): validated programs
    only, most recent first, then in program order; `None` otherwise."""
    async for module in _teaching_modules(db, user_id):
        if norm_name in _norms(module):
            return SkillModule(module.id, module.program_id, module.title)
    return None


async def _teaching_modules(db: AsyncSession, user_id: str) -> AsyncIterator[Module]:
    for program in await ProgramRepository(db, user_id).list_recent():
        if program.status != "validated":
            continue
        for module in (await load(db, user_id, program.id)).modules:
            if not module.skipped:
                yield module


async def teaching_module_ids(db: AsyncSession, user_id: str) -> dict[str, list[str]]:
    """Modules teaching each normalized skill, in the same order."""
    modules: dict[str, list[str]] = {}
    async for module in _teaching_modules(db, user_id):
        for norm in dict.fromkeys(_norms(module)):
            modules.setdefault(norm, []).append(module.id)
    return modules


async def program_skill_names(db: AsyncSession, user_id: str, program_id: str) -> list[str]:
    """The skills of the program's modules (skipped ones included: they remain expected by the
    target), in program order, once each, normalized names; 404 if the program is not the user's."""
    loaded = await load(db, user_id, program_id)
    return list(dict.fromkeys(norm for module in loaded.modules for norm in _norms(module)))


async def skill_weeks(db: AsyncSession, user_id: str) -> dict[str, int]:
    """`normalized name → week` of the skills taught by a non-skipped module of a validated program
    (most recent first, then program order; the first module wins). The week is that of the
    module's first task (rank of the program week that contains its date), otherwise that of the
    module (offer gap, D122)."""
    return (await skill_coverage(db, user_id)).weeks


async def skill_coverage(db: AsyncSession, user_id: str) -> SkillCoverage:
    """Weeks of general coverage and of the additions validated under « Compétences des offres »."""
    coverage = SkillCoverage({}, {})
    for program in await ProgramRepository(db, user_id).list_recent():
        if program.status != "validated":
            continue
        loaded = await load(db, user_id, program.id)
        rank = {week.id: week.rank for week in loaded.weeks}
        for module in loaded.modules:
            if module.skipped:
                continue
            tasks = loaded.tasks_of_module(module.id)
            week = loaded.week_of(tasks[0].planned_date) if tasks else None
            number = week.rank if week is not None else rank.get(module.week_id)
            if number is None:
                continue
            for norm in _norms(module):
                coverage.weeks.setdefault(norm, number)
                if module.title in GAP_MODULE_TITLES:
                    coverage.offer_weeks.setdefault(norm, number)
    return coverage
