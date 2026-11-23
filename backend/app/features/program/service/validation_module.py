"""« Je les maîtrise déjà » (D220) : un module « Valider mes acquis » dans le programme validé, sans
tâche ni leçon ; son quiz, écrit d'après les compétences, les fait passer à « validé » s'il est
réussi (même notation que tout quiz de module)."""

import logging
from collections.abc import Sequence
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.program import Week
from app.features.program.repository import ModuleRepository
from app.features.program.service.module_kinds import VALIDATION_KIND
from app.features.program.service.programs import load
from app.features.program.service.runtime import ProgramRuntime
from app.features.program.service.structure import MAX_MODULES_PER_WEEK, week_full

logger = logging.getLogger(__name__)

__all__ = ["VALIDATION_BRIEF", "VALIDATION_KIND", "add_validation_module", "is_validation_module"]

_TITLE = "Valider mes acquis : "


def _week(weeks: Sequence[Week], counts: dict[str, int], today: date) -> Week | None:
    """La semaine en cours (ou la première à venir) qui a encore de la place, sinon la dernière
    qui en a ; `None` si toutes sont pleines."""
    ordered = sorted(weeks, key=lambda w: w.rank)
    roomy = [w for w in ordered if counts.get(w.id, 0) < MAX_MODULES_PER_WEEK]
    current = [w for w in roomy if w.start_date + timedelta(days=7) > today]
    found = current or roomy[-1:]
    return found[0] if found else None


async def add_validation_module(
    rt: ProgramRuntime, user_id: str, program_id: str, skills: Sequence[str], today: date
) -> str:
    """Rend l'id du module ajouté ; 409 `week_full` si aucune semaine n'a de place."""
    async with rt.program_lock(user_id, program_id), rt.session_factory() as db:
        loaded = await load(db, user_id, program_id)
        counts: dict[str, int] = {}
        for module in loaded.modules:
            counts[module.week_id] = counts.get(module.week_id, 0) + 1
        week = _week(loaded.weeks, counts, today)
        if week is None:
            raise week_full()
        mine = [m for m in loaded.modules if m.week_id == week.id]
        module = await ModuleRepository(db, user_id).add(
            week_id=week.id,
            program_id=program_id,
            rank=max((m.rank for m in mine), default=-1) + 1,
            title=(_TITLE + ", ".join(skills))[:200],
            skills=list(skills)[:8],
            prerequisites=[],
            skipped=False,
            kind=VALIDATION_KIND,
        )
        await db.commit()
        module_id = module.id
    logger.info("Module de validation ajouté : programme %s, module %s", program_id, module_id)
    return module_id


# Tient lieu de leçon pour l'Examinateur (le quiz d'un module de validation n'en a pas).
VALIDATION_BRIEF = (
    "Aucune leçon : ce module vérifie des acquis que January dit déjà maîtriser. Écris des "
    "questions de niveau professionnel qui ne se réussissent qu'en maîtrisant réellement les "
    "compétences du module (pratique, cas concrets, pièges courants), sans t'appuyer sur un cours."
)


async def is_validation_module(db: AsyncSession, user_id: str, module_id: str) -> bool:
    module = await ModuleRepository(db, user_id).get(module_id)
    return module is not None and module.kind == VALIDATION_KIND
