"""Weeks and modules written directly (phase 10, 10.W): January or Claude (through MCP) adds a
week at the end of the program, a module to a week, or edits their text, without an agent. The
tasks of a module are added afterwards through `PATCH /programs/{id}` (`add_tasks`), which
checks the week rule (85%, practice, quiz): a new week or module therefore has nothing to
check yet. Everything happens under the program lock, on the re-read state."""

import logging
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.program import Module, Week
from app.features.program.repository import ModuleRepository, WeekRepository
from app.features.program.schemas import (
    ModuleCreate,
    ModuleOut,
    ModulePatch,
    WeekCreate,
    WeekOut,
    WeekPatch,
)
from app.features.program.service.editing import module_not_found
from app.features.program.service.programs import DAYS_PER_WEEK, Loaded, load, view_of
from app.features.program.service.runtime import ProgramRuntime

logger = logging.getLogger(__name__)

MAX_WEEKS = 52
MAX_MODULES_PER_WEEK = 4


def week_not_found() -> AppError:
    return AppError("week_not_found", "Week not found.", 404)


def too_many_weeks() -> AppError:
    return AppError("too_many_weeks", f"A program has {MAX_WEEKS} weeks at most.", 409)


def week_full() -> AppError:
    return AppError("week_full", f"A week has {MAX_MODULES_PER_WEEK} modules at most.", 409)


async def _week_program(rt: ProgramRuntime, user_id: str, week_id: str) -> str:
    async with rt.session_factory() as db:
        week = await WeekRepository(db, user_id).get(week_id)
    if week is None:
        raise week_not_found()
    return week.program_id


async def _module_program(rt: ProgramRuntime, user_id: str, module_id: str) -> str:
    async with rt.session_factory() as db:
        module = await ModuleRepository(db, user_id).get(module_id)
    if module is None:
        raise module_not_found()
    return module.program_id


async def _week_view(db: AsyncSession, user_id: str, program_id: str, week_id: str) -> WeekOut:
    view = await view_of(db, user_id, await load(db, user_id, program_id))
    return next(week for week in view.weeks if week.id == week_id)


async def _module_view(
    db: AsyncSession, user_id: str, program_id: str, module_id: str
) -> ModuleOut:
    view = await view_of(db, user_id, await load(db, user_id, program_id))
    return next(m for week in view.weeks for m in week.modules if m.id == module_id)


def _next_start(loaded: Loaded) -> date:
    if not loaded.weeks:
        return loaded.program.start_date
    return loaded.weeks[-1].start_date + timedelta(days=DAYS_PER_WEEK)


async def add_week(rt: ProgramRuntime, user_id: str, program_id: str, body: WeekCreate) -> WeekOut:
    """A week at the end of the program (404 `program_not_found`, 409 `too_many_weeks`)."""
    async with rt.program_lock(user_id, program_id), rt.session_factory() as db:
        loaded = await load(db, user_id, program_id)
        if len(loaded.weeks) >= MAX_WEEKS:
            raise too_many_weeks()
        week = await WeekRepository(db, user_id).add(
            program_id=program_id,
            rank=max((w.rank for w in loaded.weeks), default=0) + 1,
            theme=body.theme,
            objective=body.objective,
            deliverable=body.deliverable,
            start_date=_next_start(loaded),
        )
        await db.commit()
        week_id = week.id
        out = await _week_view(db, user_id, program_id, week_id)
    logger.info("Week added: program %s, week %s", program_id, week_id)
    return out


async def patch_week(rt: ProgramRuntime, user_id: str, week_id: str, patch: WeekPatch) -> WeekOut:
    program_id = await _week_program(rt, user_id, week_id)
    async with rt.program_lock(user_id, program_id), rt.session_factory() as db:
        week: Week | None = await WeekRepository(db, user_id).get(week_id)
        if week is None:
            raise week_not_found()
        for name, value in patch.model_dump(exclude_none=True).items():
            setattr(week, name, value)
        await db.commit()
        out = await _week_view(db, user_id, program_id, week_id)
    logger.info("Week edited: program %s, week %s", program_id, week_id)
    return out


async def add_module(
    rt: ProgramRuntime, user_id: str, program_id: str, body: ModuleCreate
) -> ModuleOut:
    """A module in a week of the program (404 `program_not_found` or `week_not_found`, 409
    `week_full`)."""
    async with rt.program_lock(user_id, program_id), rt.session_factory() as db:
        loaded = await load(db, user_id, program_id)
        if not any(week.id == body.week_id for week in loaded.weeks):
            raise week_not_found()
        mine = [m for m in loaded.modules if m.week_id == body.week_id]
        if len(mine) >= MAX_MODULES_PER_WEEK:
            raise week_full()
        module = await ModuleRepository(db, user_id).add(
            week_id=body.week_id,
            program_id=program_id,
            rank=max((m.rank for m in mine), default=-1) + 1,  # modules are counted from 0
            title=body.title,
            skills=list(body.skills),
            prerequisites=list(body.prerequisites),
            skipped=False,
        )
        await db.commit()
        module_id = module.id
        out = await _module_view(db, user_id, program_id, module_id)
    logger.info("Module added: program %s, module %s", program_id, module_id)
    return out


async def patch_module(
    rt: ProgramRuntime, user_id: str, module_id: str, patch: ModulePatch
) -> ModuleOut:
    program_id = await _module_program(rt, user_id, module_id)
    async with rt.program_lock(user_id, program_id), rt.session_factory() as db:
        module: Module | None = await ModuleRepository(db, user_id).get(module_id)
        if module is None:
            raise module_not_found()
        for name, value in patch.model_dump(mode="json", exclude_none=True).items():
            setattr(module, name, list(value) if isinstance(value, list) else value)
        await db.commit()
        out = await _module_view(db, user_id, program_id, module_id)
    logger.info("Module edited: program %s, module %s", program_id, module_id)
    return out
