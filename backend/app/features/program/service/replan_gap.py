"""Le module « Compétences des offres » d'un programme (« Ajouter au planning », SPEC F8, D123).

Il reçoit les ajouts d'une replanification au déclencheur `gap`. **Créé en fin de programme à la
1re application, puis réutilisé** : un module existant a déjà son objectif, y glisser une
compétence d'offre fausserait sa couverture. Tant qu'il n'existe pas, la proposition le vise par
un id provisoire (`NEW_GAP_MODULE`) : un module vide ajouté à la dernière semaine des lignes
rangées (`with_gap_module`), jamais écrit avant l'acceptation. À l'acceptation, il est créé (ou
retrouvé) et reçoit les compétences des tâches ajoutées : la ligne de l'écart passe alors
`in_program`. Il se reconnaît à son titre (un titre de module ne se modifie pas)."""

from collections.abc import Sequence
from dataclasses import replace

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.replan_port import GAP_MODULE_TITLE, GAP_MODULE_TITLES
from app.core.skills import normalize_skill_name
from app.db.models.program import Module
from app.features.program.repository import ModuleRepository, ProgramRepository
from app.features.program.service.diff import ModuleRow, ProgramRows
from app.features.program.service.programs import Loaded
from app.features.program.service.replan_rows import NewTask, PlannedTask

NEW_GAP_MODULE = "module-competences-des-offres"  # id provisoire, jamais en base


async def latest_validated(db: AsyncSession, user_id: str) -> str | None:
    """Le programme validé le plus récent de January, `None` s'il n'y en a pas."""
    programs = await ProgramRepository(db, user_id).list_recent()
    return next((p.id for p in programs if p.status == "validated"), None)


def gap_module(loaded: Loaded) -> Module | None:
    """Le module « Compétences des offres » du programme (non sauté), s'il existe."""
    found = [m for m in loaded.modules if m.title in GAP_MODULE_TITLES and not m.skipped]
    return found[-1] if found else None


def gap_module_id(loaded: Loaded) -> str:
    """L'id du module cible : le module existant, sinon l'id provisoire."""
    module = gap_module(loaded)
    return module.id if module is not None else NEW_GAP_MODULE


def with_gap_module(rows: ProgramRows, add: Sequence[NewTask]) -> ProgramRows:
    """Les lignes avec le module provisoire, vide, en fin de dernière semaine, quand un ajout le
    vise : le rangement place l'ajout dans cette semaine (ou plus tard si elle est passée ou
    pleine), et l'instantané le montre dans « Compétences des offres »."""
    if not rows.weeks or all(task.module_id != NEW_GAP_MODULE for task in add):
        return rows
    last = rows.weeks[-1]
    module = ModuleRow(GAP_MODULE_TITLE, module_id=NEW_GAP_MODULE)
    return ProgramRows([*rows.weeks[:-1], replace(last, modules=[*last.modules, module])])


def _merged(current: Sequence[object], skills: Sequence[str]) -> list[str]:
    names = [str(name) for name in current]
    seen = {normalize_skill_name(name) for name in names}
    for skill in skills:
        norm = normalize_skill_name(skill)
        if norm and norm not in seen:
            seen.add(norm)
            names.append(skill)
    return names


async def gap_target(
    db: AsyncSession,
    user_id: str,
    loaded: Loaded,
    skills: Sequence[str],
    tasks: Sequence[PlannedTask],
) -> str:
    """À l'acceptation : l'id du module « Compétences des offres », créé à la fin de la dernière
    semaine s'il n'existe pas, avec les compétences `skills` en plus des siennes (dédoublonnées,
    noms normalisés). Chaîne vide si la version n'ajoute rien au module."""
    if not skills and all(task.module_id != NEW_GAP_MODULE for task in tasks):
        return ""
    module = gap_module(loaded)
    if module is None:
        week = loaded.weeks[-1]
        ranks = [m.rank for m in loaded.modules if m.week_id == week.id]
        module = await ModuleRepository(db, user_id).add(
            week_id=week.id,
            program_id=loaded.program.id,
            rank=max(ranks, default=-1) + 1,
            title=GAP_MODULE_TITLE,
            skills=[],
        )
    module.skills = _merged(module.skills, skills)
    return module.id
