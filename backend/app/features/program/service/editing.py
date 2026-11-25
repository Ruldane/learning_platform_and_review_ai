"""January's edits to a program (SPEC 3.4, D88): move or edit a task, add and remove tasks,
shift a draft's start date.

Everything happens under `program_lock(user_id, program_id)`, on the state re-read in a new
session: the week rules (85% of the budget, at least one practice, one quiz) are checked on
each touched week before the commit. Two moves that each hold but not together: the second
sees the first and receives a readable 422, without echoing the input."""

import logging
from collections.abc import Iterable
from datetime import timedelta
from typing import cast

from app.core.errors import AppError
from app.db.models.program import Task, TaskType, Week
from app.features.program.repository import TaskRepository
from app.features.program.schemas import ProgramOut, ProgramPatch, TaskOut, TaskPatch
from app.features.program.service.programs import Loaded, load, task_out, view_of
from app.features.program.service.rules import WeekRule, week_breaks
from app.features.program.service.runtime import ProgramRuntime

logger = logging.getLogger(__name__)

MONDAY = 0


class WeekRuleBroken(AppError):
    """A week rule would be broken; `details`: rank, load and cap (numbers)."""

    def __init__(
        self, code: str, message: str, week: Week | None, planned: int | None, cap: int
    ) -> None:
        details = {
            "week_rank": week.rank if week is not None else None,
            "planned_minutes": planned,
            "cap_minutes": cap,
        }
        super().__init__(code, message, 422, details)


def task_not_found() -> AppError:
    return AppError("task_not_found", "Task not found.", 404)


def module_not_found() -> AppError:
    return AppError("module_not_found", "Module not found.", 404)


def _outside(cap: int) -> WeekRuleBroken:
    return WeekRuleBroken(
        "date_outside_program", "Choose a day within the program.", None, None, cap
    )


_MESSAGES: dict[WeekRule, str] = {
    "week_over_budget": (
        "{label} would exceed 85% of your budget. {total} min planned, limit {cap} min."
    ),
    "week_needs_practice": "{label} needs at least one practice task.",
    "week_needs_quiz": "{label} needs a quiz.",
}


def check_weeks(loaded: Loaded, weeks: Iterable[Week | None]) -> None:
    """Rule of each given week (`rules.week_breaks`, the same as for the Strategist), on the
    tasks planned within its seven days: the first one broken raises `WeekRuleBroken`."""
    cap = loaded.program.cap_minutes
    for week in sorted({w for w in weeks if w is not None}, key=lambda w: w.rank):
        tasks = [
            (t.minutes, cast(TaskType, t.type))
            for t in loaded.tasks
            if loaded.week_of(t.planned_date) is week
        ]
        total = sum(minutes for minutes, _ in tasks)
        for rule in week_breaks(tasks, cap):
            label = f"Week {week.rank}"
            message = _MESSAGES[rule].format(label=label, total=total, cap=cap)
            raise WeekRuleBroken(rule, message, week, total, cap)


def _apply(loaded: Loaded, task: Task, patch: TaskPatch) -> set[Week | None]:
    """Applies the edit; returns the touched weeks (load or type changed)."""
    touched: set[Week | None] = set()
    if patch.planned_date is not None and patch.planned_date != task.planned_date:
        target = loaded.week_of(patch.planned_date)
        if target is None:
            raise _outside(loaded.program.cap_minutes)
        touched |= {loaded.week_of(task.planned_date), target}
        task.planned_date = patch.planned_date
    if patch.minutes is not None and patch.minutes != task.minutes:
        task.minutes = patch.minutes
        touched.add(loaded.week_of(task.planned_date))
    if patch.title is not None:
        task.title = patch.title
    if patch.status is not None:
        task.status = patch.status
    return touched


async def move_or_edit_task(
    rt: ProgramRuntime, user_id: str, task_id: str, patch: TaskPatch
) -> TaskOut:
    """Moves or edits a task (day, duration, title, status) under the program lock."""
    async with rt.session_factory() as db:
        program_id = await TaskRepository(db, user_id).program_of(task_id)
    if program_id is None:
        raise task_not_found()
    async with rt.program_lock(user_id, program_id), rt.session_factory() as db:
        loaded = await load(db, user_id, program_id)
        task = next((t for t in loaded.tasks if t.id == task_id), None)
        if task is None:
            raise task_not_found()
        check_weeks(loaded, _apply(loaded, task, patch))
        await db.commit()
        out = task_out(task)
    logger.info("Task edited: user %s, program %s, task %s", user_id, program_id, task_id)
    return out


def _shift(loaded: Loaded, patch: ProgramPatch) -> None:
    """Shifts the whole draft (weeks and tasks) to a new start date, a Monday."""
    program, start = loaded.program, patch.start_date
    if start is None or start == program.start_date:
        return
    if program.status != "draft":
        raise AppError("program_validated", "A validated program has a fixed start date.", 409)
    if start.weekday() != MONDAY:
        raise AppError(
            "invalid_start_date",
            "A program must start on a Monday.",
            422,
            {"fields": ["start_date"]},
        )
    delta: timedelta = start - program.start_date
    for week in loaded.weeks:
        week.start_date += delta
    for task in loaded.tasks:
        task.planned_date += delta
    program.start_date = start


async def _delete(loaded: Loaded, repo: TaskRepository, ids: list[str]) -> set[Week | None]:
    by_id = {task.id: task for task in loaded.tasks}
    if any(task_id not in by_id for task_id in ids):
        raise task_not_found()
    touched = {loaded.week_of(by_id[task_id].planned_date) for task_id in ids}
    await repo.delete_many(ids)
    loaded.tasks = [task for task in loaded.tasks if task.id not in set(ids)]
    return touched


async def _add(loaded: Loaded, repo: TaskRepository, patch: ProgramPatch) -> set[Week | None]:
    modules = {m.id: m for m in loaded.modules if not m.skipped}
    touched: set[Week | None] = set()
    for new in patch.add_tasks:
        if new.module_id not in modules:
            raise module_not_found()
        week = loaded.week_of(new.planned_date)
        if week is None:
            raise _outside(loaded.program.cap_minutes)
        task = await repo.add(
            **new.model_dump(),
            program_id=loaded.program.id,
            rank=await repo.next_rank(new.module_id),
            status="todo",
            already_known=False,
        )
        loaded.tasks.append(task)
        touched.add(week)
    return touched


async def add_and_delete(
    rt: ProgramRuntime, user_id: str, program_id: str, patch: ProgramPatch
) -> ProgramOut:
    """Start date (draft), removals then additions, applied together under the lock: a broken
    rule cancels everything (nothing is committed)."""
    async with rt.program_lock(user_id, program_id), rt.session_factory() as db:
        loaded = await load(db, user_id, program_id)
        repo = TaskRepository(db, user_id)
        _shift(loaded, patch)
        touched = await _delete(loaded, repo, list(dict.fromkeys(patch.delete_task_ids)))
        touched |= await _add(loaded, repo, patch)
        check_weeks(loaded, touched)
        await db.commit()
        view = await view_of(db, user_id, loaded)
    logger.info(
        "Program edited: user %s, program %s, %d addition(s), %d removal(s)",
        user_id,
        program_id,
        len(patch.add_tasks),
        len(patch.delete_task_ids),
    )
    return view
