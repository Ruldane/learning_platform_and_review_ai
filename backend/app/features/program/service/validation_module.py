""" "I already master them" (D220): a "Validate my skills" module in the validated program,
with no task or lesson; its quiz, written from the skills, moves them to "validated" if
passed (same grading as any module quiz)."""

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
    """The current week (or the first upcoming one) that still has room, otherwise the last
    one that has; `None` if all are full."""
    ordered = sorted(weeks, key=lambda w: w.rank)
    roomy = [w for w in ordered if counts.get(w.id, 0) < MAX_MODULES_PER_WEEK]
    current = [w for w in roomy if w.start_date + timedelta(days=7) > today]
    found = current or roomy[-1:]
    return found[0] if found else None


async def add_validation_module(
    rt: ProgramRuntime, user_id: str, program_id: str, skills: Sequence[str], today: date
) -> str:
    """Returns the id of the added module; 409 `week_full` if no week has room."""
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
    logger.info("Validation module added: program %s, module %s", program_id, module_id)
    return module_id


# Stands in for the lesson for the Examiner (a validation module's quiz has none).
VALIDATION_BRIEF = (
    "No lesson: this module checks skills January says she already masters. Write "
    "professional-level questions that can only be passed by really mastering the module's "
    "skills (practice, concrete cases, common pitfalls), without relying on a course."
)


async def is_validation_module(db: AsyncSession, user_id: str, module_id: str) -> bool:
    module = await ModuleRepository(db, user_id).get(module_id)
    return module is not None and module.kind == VALIDATION_KIND
