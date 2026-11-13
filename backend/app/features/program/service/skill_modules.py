"""Les compétences vues depuis les modules (lecture pour la carte de compétences, D107) : le
module qui enseigne une compétence (prochaine action) et les compétences d'un programme (cible
de la comparaison). Les noms sont comparés normalisés (`normalize_skill_name`)."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.skills import normalize_skill_name
from app.db.models.program import Module
from app.features.program.repository import ProgramRepository
from app.features.program.service.programs import load


@dataclass(frozen=True)
class SkillModule:
    module_id: str
    program_id: str
    title: str


def _norms(module: Module) -> list[str]:
    return [norm for norm in (normalize_skill_name(str(s)) for s in module.skills) if norm]


async def module_teaching(db: AsyncSession, user_id: str, norm_name: str) -> SkillModule | None:
    """Le premier module non sauté qui enseigne la compétence (nom normalisé) : programmes
    validés seulement, le plus récent d'abord, puis dans l'ordre du programme ; `None` sinon."""
    for program in await ProgramRepository(db, user_id).list_recent():
        if program.status != "validated":
            continue
        for module in (await load(db, user_id, program.id)).modules:
            if not module.skipped and norm_name in _norms(module):
                return SkillModule(module.id, program.id, module.title)
    return None


async def program_skill_names(db: AsyncSession, user_id: str, program_id: str) -> list[str]:
    """Les compétences des modules du programme (sautés compris : ils restent attendus par la
    cible), dans l'ordre du programme, une fois chacune, noms normalisés ; 404 si le programme
    n'est pas à l'utilisateur."""
    loaded = await load(db, user_id, program_id)
    return list(dict.fromkeys(norm for module in loaded.modules for norm in _norms(module)))
