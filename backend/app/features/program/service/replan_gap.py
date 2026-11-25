"""The "Postings skills" module of a program ("Add to the plan", SPEC F8, D123).

It receives the additions of a replanning with the `gap` trigger. **Created at the end of the
program on the 1st application, then reused**: an existing module already has its goal, slipping
a posting skill into it would skew its coverage. As long as it does not exist, the proposal
targets it with a provisional id (`NEW_GAP_MODULE`): an empty module added to the last week of
the packed rows (`with_gap_module`), never written before acceptance. On acceptance, it is
created (or found) and receives the skills of the added tasks: the gap row then becomes
`in_program`. It is recognised by its title (a module title cannot be edited)."""

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

NEW_GAP_MODULE = "module-postings-skills"  # provisional id, never in the database
# Proposals stored before the switch to English may carry the French provisional id.
LEGACY_NEW_GAP_MODULE = "module-competences-des-offres"


async def latest_validated(db: AsyncSession, user_id: str) -> str | None:
    """January's most recent validated program, `None` if there is none."""
    programs = await ProgramRepository(db, user_id).list_recent()
    return next((p.id for p in programs if p.status == "validated"), None)


def gap_module(loaded: Loaded) -> Module | None:
    """The program's "Postings skills" module (not skipped), if it exists."""
    found = [m for m in loaded.modules if m.title in GAP_MODULE_TITLES and not m.skipped]
    return found[-1] if found else None


def gap_module_id(loaded: Loaded) -> str:
    """The id of the target module: the existing module, otherwise the provisional id."""
    module = gap_module(loaded)
    return module.id if module is not None else NEW_GAP_MODULE


def with_gap_module(rows: ProgramRows, add: Sequence[NewTask]) -> ProgramRows:
    """The rows with the provisional, empty module at the end of the last week, when an addition
    targets it: the packing places the addition in that week (or later if it is past or full),
    and the snapshot shows it in "Postings skills"."""
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
    """On acceptance: the id of the "Postings skills" module, created at the end of the last
    week if it does not exist, with the skills `skills` added to its own (deduplicated,
    normalized names). Empty string if the version adds nothing to the module."""
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
