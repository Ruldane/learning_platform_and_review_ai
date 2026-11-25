"""Following up a quiz in the program (SPEC F9, D101): review tasks and new attempt placed in
the budget, the week's `quiz` task and "Retake the quiz" tasks ticked.

All these functions assume the program lock is ALREADY HELD by the caller
(`ProgramRuntime.program_lock`, taken before the write transaction, F4): they read the rows,
write in the `db` session and do not commit. A week's rule is that of 4.2 (`rules.week_breaks`:
85% of the budget, a practice, a quiz): a task only goes on a day whose week stays compliant
after the addition; otherwise it is not placed (counted)."""

import builtins
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.program import Task, TaskType, Week
from app.features.program.repository import TaskRepository
from app.features.program.service.programs import Loaded, load, program_of_module
from app.features.program.service.rules import RETRY_PREFIX, RETRY_PREFIXES, week_breaks
from app.features.program.service.runtime import ProgramRuntime
from app.features.quiz.service.graded import graded_modules

SUNDAY = 6  # free Sunday (SPEC 3.4): no follow-up task is placed on it
TITLE_MAX = 200


@dataclass(frozen=True)
class FollowupTask:
    title: str
    type: TaskType
    minutes: int
    done_criterion: str
    earliest: date


def retry_title(module_title: str) -> str:
    return f"{RETRY_PREFIX}{module_title}"[:TITLE_MAX]


def _fits(loaded: Loaded, week: Week, new: FollowupTask) -> bool:
    tasks = [
        (t.minutes, cast(TaskType, t.type))
        for t in loaded.tasks
        if loaded.week_of(t.planned_date) is week
    ]
    return not week_breaks([*tasks, (new.minutes, new.type)], loaded.program.cap_minutes)


def _first_day(loaded: Loaded, new: FollowupTask) -> date | None:
    """First day ≥ `earliest`, except Sunday, in a program week that stays compliant with the
    task; `None` if there is none."""
    if not loaded.weeks:
        return None
    end = loaded.weeks[-1].start_date + timedelta(days=7)
    day = max(new.earliest, loaded.weeks[0].start_date)
    while day < end:
        week = loaded.week_of(day)
        if day.weekday() != SUNDAY and week is not None and _fits(loaded, week, new):
            return day
        day += timedelta(days=1)
    return None


async def add_followup(
    db: AsyncSession,
    runtime: ProgramRuntime,
    user_id: str,
    module_id: str,
    tasks: Sequence[FollowupTask],
) -> tuple[list[date], int]:
    """Places each task on the first possible day (module `module_id`); returns the days of the
    tasks placed, in order, and the number of tasks not placed. Lock held (F4)."""
    loaded = await load(db, user_id, await program_of_module(db, user_id, module_id))
    repo = TaskRepository(db, user_id)
    days: list[date] = []
    unplaced = 0
    for new in tasks:
        day = _first_day(loaded, new)
        if day is None:
            unplaced += 1
            continue
        task = await repo.add(
            module_id=module_id,
            program_id=loaded.program.id,
            rank=await repo.next_rank(module_id),
            title=new.title[:TITLE_MAX],
            type=new.type,
            minutes=new.minutes,
            done_criterion=new.done_criterion,
            planned_date=day,
            status="todo",
            already_known=False,
        )
        loaded.tasks.append(task)
        days.append(day)
    return days, unplaced


def _done(tasks: Sequence[Task]) -> builtins.list[Task]:
    todo = [t for t in tasks if t.status != "done"]
    for task in todo:
        task.status = "done"
    return todo


async def tick_retry(
    db: AsyncSession, runtime: ProgramRuntime, user_id: str, module_id: str
) -> int:
    """Ticks the module's "Retake the quiz" tasks still to do (F18); returns their number.
    Idempotent. Lock held (F4)."""
    loaded = await load(db, user_id, await program_of_module(db, user_id, module_id))
    retries = [
        t
        for t in loaded.tasks_of_module(module_id)
        if t.type == "quiz" and t.title.startswith(RETRY_PREFIXES)
    ]
    ticked = _done(retries)
    await db.flush()
    return len(ticked)


async def tick_week_quiz(
    db: AsyncSession, runtime: ProgramRuntime, user_id: str, module_id: str
) -> bool:
    """Ticks the `quiz` task of the module's week (those of this week's modules, excluding
    "Retake the quiz") when each non-skipped module of the week has a graded attempt; returns
    true if a task has just been ticked. Idempotent. Lock held (F4)."""
    loaded = await load(db, user_id, await program_of_module(db, user_id, module_id))
    module = next(m for m in loaded.modules if m.id == module_id)
    week_modules = [m for m in loaded.modules if m.week_id == module.week_id and not m.skipped]
    graded = await graded_modules(db, user_id, [m.id for m in week_modules])
    if any(m.id not in graded for m in week_modules):
        return False
    ids = {m.id for m in week_modules}
    quizzes = [
        t
        for t in loaded.tasks
        if t.module_id in ids and t.type == "quiz" and not t.title.startswith(RETRY_PREFIXES)
    ]
    ticked = _done(quizzes)
    await db.flush()
    return bool(ticked)


async def tick_tasks(
    db: AsyncSession, runtime: ProgramRuntime, user_id: str, task_ids: Sequence[str]
) -> builtins.list[str]:
    """Ticks the user's tasks still to do among `task_ids`; returns their titles. An unknown or
    another user's task is ignored. Idempotent. Lock held (F4)."""
    repo = TaskRepository(db, user_id)
    found = [task for task_id in dict.fromkeys(task_ids) if (task := await repo.get_fresh(task_id))]
    ticked = _done(found)
    await db.flush()
    return [task.title for task in ticked]


async def program_of_task(db: AsyncSession, user_id: str, task_id: str) -> str | None:
    """The program of one of the user's tasks (`None`: unknown or another user's), to take its
    lock before ticking it (F4). Read for the other features (contract 2)."""
    task = await TaskRepository(db, user_id).get(task_id)
    return None if task is None else task.program_id
