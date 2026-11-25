"""Links from a capture to the program (D108, F7): the modules not skipped in January's
validated programs (`m1…`, in program order, newest first, then by position in the program)
and their dated to-do tasks within ±7 days of January's day (`t1…`, by day, then by program
order). The references are stable within a snapshot; the ids never go to the model."""

from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.capture_port import ProgramLinks
from app.agents.tools.replan_port import ModuleRef, TaskRef
from app.features.program.service.programs import Loaded, list_programs, load

WINDOW_DAYS = 7
MAX_TASKS = 60  # beyond this, the prompt grows without helping the Archivist


async def _validated(db: AsyncSession, user_id: str) -> list[Loaded]:
    programs = await list_programs(db, user_id)
    return [await load(db, user_id, p.id) for p in programs if p.status == "validated"]


def _refs(loaded: list[Loaded], today: date) -> ProgramLinks:
    first, last = today - timedelta(days=WINDOW_DAYS), today + timedelta(days=WINDOW_DAYS)
    modules = [m for one in loaded for m in one.modules if not m.skipped]
    refs = {m.id: f"m{n}" for n, m in enumerate(modules, start=1)}
    tasks = [t for one in loaded for t in one.tasks]
    order = {t.id: n for n, t in enumerate(tasks)}
    todo = sorted(
        (
            t
            for t in tasks
            if t.status == "todo" and t.module_id in refs and first <= t.planned_date <= last
        ),
        key=lambda t: (t.planned_date, order[t.id]),
    )[:MAX_TASKS]
    return ProgramLinks(
        [ModuleRef(refs[m.id], m.title, [str(s) for s in m.skills], m.id) for m in modules],
        [
            TaskRef(
                f"t{n}",
                t.title,
                t.type,  # type: ignore[arg-type]  # text column; values of TaskType
                t.minutes,
                t.planned_date,
                refs[t.module_id],
                t.planned_date < today,
                t.id,
            )
            for n, t in enumerate(todo, start=1)
        ],
    )


async def program_links(db: AsyncSession, user_id: str, today: date) -> ProgramLinks:
    return _refs(await _validated(db, user_id), today)
