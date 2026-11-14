"""Comparaison de la carte avec une cible (SPEC F15, D107 n° 2, D123) : « poste cible » = les
compétences du programme de l'objectif ; « offre précise » = les compétences apprenables de
l'offre ; attendues au niveau `valide`. Lecture seule, hors de `service` comme `map` (cycle avec
`program`) ; l'objectif est lu par `learning.service`, le programme par `program.service`,
l'offre par `gap.service` (contrat 2)."""

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


async def _compare(db: AsyncSession, user_id: str, label: str, names: list[str]) -> CompareOut:
    """Une ligne par compétence de `names` (noms normalisés, dans leur ordre) présente au
    référentiel, cible `valide` ; `coverage` = part des lignes atteintes, en %, 0,5 arrondi
    au-dessus (0 sans ligne)."""
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
    """Les compétences du programme de l'objectif, dans son ordre (voir `_compare`)."""
    label, program_id = await _target(db, user_id, goal_id)
    return await _compare(db, user_id, label, await program_skill_names(db, user_id, program_id))


async def compare_with_posting(db: AsyncSession, user_id: str, posting_id: str) -> CompareOut:
    """« Moi face à cette offre » (D123) : ses compétences apprenables (nom rattaché au
    référentiel, sinon celui du besoin), dans l'ordre de l'analyse, attendues `valide` ;
    libellé « Titre — Entreprise ». 404 `posting_not_found`, ou `no_compare_target` tant que
    l'offre n'est pas analysée."""
    found = await posting_skills(db, user_id, posting_id)
    if found is None:
        message = "Cette offre n'est pas encore analysée : rien à comparer pour l'instant."
        raise AppError("no_compare_target", message, 404)
    return await _compare(db, user_id, found.label, found.names)


def posting_id_required() -> AppError:
    return AppError(
        "posting_id_required", "Choisis l'offre à comparer.", 422, {"fields": ["posting_id"]}
    )


async def compare_with(
    db: AsyncSession,
    user_id: str,
    target: CompareTarget,
    *,
    goal_id: str | None,
    posting_id: str | None,
) -> CompareOut:
    """La comparaison demandée ; `posting` sans `posting_id` : 422 `posting_id_required`."""
    if target == "goal":
        return await compare_with_goal(db, user_id, goal_id)
    if posting_id is None:
        raise posting_id_required()
    return await compare_with_posting(db, user_id, posting_id)
