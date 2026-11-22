"""Les compétences vues depuis les modules (lecture pour la carte de compétences, D107) : le
module qui enseigne une compétence (prochaine action) et les compétences d'un programme (cible
de la comparaison). Les noms sont comparés normalisés (`normalize_skill_name`)."""

from collections.abc import AsyncIterator
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.replan_port import GAP_MODULE_TITLE
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
    """Le premier module non sauté qui enseigne la compétence (nom normalisé) : programmes
    validés seulement, le plus récent d'abord, puis dans l'ordre du programme ; `None` sinon."""
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
    """Modules enseignant chaque compétence normalisée, dans le même ordre."""
    modules: dict[str, list[str]] = {}
    async for module in _teaching_modules(db, user_id):
        for norm in dict.fromkeys(_norms(module)):
            modules.setdefault(norm, []).append(module.id)
    return modules


async def program_skill_names(db: AsyncSession, user_id: str, program_id: str) -> list[str]:
    """Les compétences des modules du programme (sautés compris : ils restent attendus par la
    cible), dans l'ordre du programme, une fois chacune, noms normalisés ; 404 si le programme
    n'est pas à l'utilisateur."""
    loaded = await load(db, user_id, program_id)
    return list(dict.fromkeys(norm for module in loaded.modules for norm in _norms(module)))


async def skill_weeks(db: AsyncSession, user_id: str) -> dict[str, int]:
    """`nom normalisé → semaine` des compétences enseignées par un module non sauté d'un
    programme validé (le plus récent d'abord, puis l'ordre du programme ; le premier module
    gagne). La semaine est celle de la 1re tâche du module (rang de la semaine du programme qui
    contient sa date), sinon celle du module (écart d'une offre, D122)."""
    return (await skill_coverage(db, user_id)).weeks


async def skill_coverage(db: AsyncSession, user_id: str) -> SkillCoverage:
    """Semaines de couverture générale et des ajouts validés dans « Compétences des offres »."""
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
                if module.title == GAP_MODULE_TITLE:
                    coverage.offer_weeks.setdefault(norm, number)
    return coverage
