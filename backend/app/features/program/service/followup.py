"""Suivi d'un quiz dans le programme (SPEC F9, D101) : tâches de révision et nouvel essai posés
dans le budget, tâche `quiz` de la semaine et tâches « Refaire le quiz » cochées.

Toutes ces fonctions supposent le verrou du programme DÉJÀ TENU par l'appelant
(`ProgramRuntime.program_lock`, pris avant la transaction d'écriture, F4) : elles lisent les
lignes, écrivent dans la session `db` et ne commitent pas. La règle d'une semaine est celle de
4.2 (`rules.week_breaks` : 85 % du budget, une pratique, un quiz) : une tâche ne va que dans un
jour dont la semaine reste conforme après l'ajout ; sinon elle n'est pas placée (comptée)."""

import builtins
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.program import Task, TaskType, Week
from app.features.program.repository import TaskRepository
from app.features.program.service.programs import Loaded, load, program_of_module
from app.features.program.service.rules import RETRY_PREFIX, week_breaks
from app.features.program.service.runtime import ProgramRuntime
from app.features.quiz.service.graded import graded_modules

SUNDAY = 6  # dimanche libre (SPEC 3.4) : aucune tâche de suivi n'y est posée
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
    """Premier jour ≥ `earliest`, hors dimanche, dans une semaine du programme qui reste
    conforme avec la tâche ; `None` s'il n'y en a pas."""
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
    """Pose chaque tâche au premier jour possible (module `module_id`) ; rend les jours des
    tâches posées, dans l'ordre, et le nombre de tâches non placées. Verrou tenu (F4)."""
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
    """Coche les tâches « Refaire le quiz » encore à faire de ce module (F18) ; rend leur
    nombre. Idempotent. Verrou tenu (F4)."""
    loaded = await load(db, user_id, await program_of_module(db, user_id, module_id))
    retries = [
        t
        for t in loaded.tasks_of_module(module_id)
        if t.type == "quiz" and t.title.startswith(RETRY_PREFIX)
    ]
    ticked = _done(retries)
    await db.flush()
    return len(ticked)


async def tick_week_quiz(
    db: AsyncSession, runtime: ProgramRuntime, user_id: str, module_id: str
) -> bool:
    """Coche la tâche `quiz` de la semaine du module (celles des modules de cette semaine, hors
    « Refaire le quiz ») quand chaque module non sauté de la semaine a une tentative notée ;
    rend vrai si une tâche vient d'être cochée. Idempotent. Verrou tenu (F4)."""
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
        if t.module_id in ids and t.type == "quiz" and not t.title.startswith(RETRY_PREFIX)
    ]
    ticked = _done(quizzes)
    await db.flush()
    return bool(ticked)


async def tick_tasks(
    db: AsyncSession, runtime: ProgramRuntime, user_id: str, task_ids: Sequence[str]
) -> builtins.list[str]:
    """Coche les tâches de l'utilisateur encore à faire parmi `task_ids` ; rend leurs titres.
    Une tâche inconnue ou d'un autre est ignorée. Idempotent. Verrou tenu (F4)."""
    repo = TaskRepository(db, user_id)
    found = [task for task_id in dict.fromkeys(task_ids) if (task := await repo.get_fresh(task_id))]
    ticked = _done(found)
    await db.flush()
    return [task.title for task in ticked]


async def program_of_task(db: AsyncSession, user_id: str, task_id: str) -> str | None:
    """Le programme d'une tâche de l'utilisateur (`None` : inconnue ou d'un autre), pour prendre
    son verrou avant de la cocher (F4). Lecture pour les autres features (contrat 2)."""
    task = await TaskRepository(db, user_id).get(task_id)
    return None if task is None else task.program_id
