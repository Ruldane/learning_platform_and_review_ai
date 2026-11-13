"""Comparaison de la carte avec une cible (SPEC F15, D107 n° 2) : « poste cible » = les
compétences du programme de l'objectif, attendues au niveau `valide` ; « offre précise » en
phase 6. Lecture seule, hors de `service` comme `map` (cycle avec `program`) ; l'objectif est lu
par `learning.service`, le programme par `program.service` (contrat 2)."""

from math import floor

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.skills import LEVEL_ORDER, SkillLevel
from app.features.learning.service.goals import get_goal, list_goals
from app.features.program.service.skill_modules import program_skill_names
from app.features.skills.radar import as_level, domain_name
from app.features.skills.repository import SkillRepository, UserSkillRepository
from app.features.skills.schemas import CompareOut, CompareRowOut

TARGET_LEVEL: SkillLevel = "valide"
LABEL_MAX = 120


def no_compare_target() -> AppError:
    message = "Aucun objectif avec un programme : rien à comparer pour l'instant."
    return AppError("no_compare_target", message, 404)


def gap(mine: SkillLevel | None, target: SkillLevel) -> int:
    """Rang de la cible moins le mien (`LEVEL_ORDER`, absente = −1) ; 0 ou moins : atteint."""
    rank = LEVEL_ORDER.index(mine) if mine is not None else -1
    return LEVEL_ORDER.index(target) - rank


async def _target(db: AsyncSession, user_id: str, goal_id: str | None) -> tuple[str, str]:
    """`(libellé, programme)` de l'objectif comparé : celui demandé (404 `goal_not_found` s'il
    n'est pas à January), sinon le plus récent qui a un programme ; 404 `no_compare_target` sans
    programme. Le libellé est le poste visé, à défaut le texte de l'objectif."""
    goals = [await get_goal(db, user_id, goal_id)] if goal_id is not None else None
    for goal in goals if goals is not None else await list_goals(db, user_id):
        if goal.program_id is not None:
            label = (goal.target_role or goal.text).strip()[:LABEL_MAX]
            return label, goal.program_id
    raise no_compare_target()


async def compare_with_goal(db: AsyncSession, user_id: str, goal_id: str | None) -> CompareOut:
    """Une ligne par compétence du programme (dans son ordre), cible `valide` ; `coverage` =
    part des lignes atteintes, en %, 0,5 arrondi au-dessus (0 sans ligne)."""
    label, program_id = await _target(db, user_id, goal_id)
    names = await program_skill_names(db, user_id, program_id)
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
