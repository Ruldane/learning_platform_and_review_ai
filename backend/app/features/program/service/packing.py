"""Placing a week's tasks on its days, never exceeding 85% of the budget.

A week is packed in two steps: the week's practice and quiz are reserved first (their minutes
are removed from the cap and from their day), then the other tasks follow in their order,
without doubling any; what no longer fits is carried to the next week. A week packed too light
then pulls tasks forward from the next one (`pull_forward`, D98). No data is written here: pure
functions, tested without a database.
"""

from collections.abc import Set
from dataclasses import dataclass, replace
from datetime import date, timedelta

from app.agents.tools.plan_schema import ModuleDraft, TaskDraft
from app.db.models.program import TaskType
from app.features.program.service.advance import Dated, WeekSlots, plan_advances
from app.features.program.service.budget import Budget
from app.features.program.service.rules import SUITE_SUFFIX, strip_suite_suffix

DAYS_PER_WEEK = 7


class NoRoom(Exception):
    """The week cannot hold its reserved tasks (practice, quiz)."""


@dataclass(frozen=True)
class Entry:
    """A task to place; `origin` = (week, module, task) of the draft, natural order.
    Replanning (D106, final review of phase 5): `not_before`, a task's current date (never
    placed before it; the reserved practice and quiz only prefer it); `retry`, a "Retake the
    quiz" (never the quiz that closes the week)."""

    task: TaskDraft
    origin: tuple[int, int, int]
    not_before: date | None = None
    retry: bool = False


@dataclass(frozen=True)
class Placement:
    entry: Entry
    day: date
    final_quiz: bool = False


@dataclass(frozen=True)
class WeekPacking:
    placed: list[Placement]
    deferred: list[Entry]


def week_days(start: date) -> list[date]:
    return [start + timedelta(days=offset) for offset in range(DAYS_PER_WEEK)]


def final_quiz(own: list[Entry]) -> Entry | None:
    """The week's last quiz: it closes the week."""
    quizzes = [entry for entry in own if entry.task.type == "quiz" and not entry.retry]
    return quizzes[-1] if quizzes else None


def first_practice(own: list[Entry]) -> Entry | None:
    """The week's first practice: its place is reserved in advance."""
    practices = [entry for entry in own if entry.task.type == "practice"]
    return practices[0] if practices else None


def _quiz_day(days: list[date], remaining: dict[date, int], minutes: int) -> date:
    """The last day that has room for the quiz (Saturday first)."""
    for day in reversed(days):
        if remaining[day] >= minutes:
            return day
    raise NoRoom


def _practice_day(usable: list[date], remaining: dict[date, int], entry: Entry) -> date:
    """The first day that has room for the practice, from its date if it has one."""
    fits = [day for day in usable if remaining[day] >= entry.task.minutes]
    later = [day for day in fits if entry.not_before is None or day >= entry.not_before]
    if not fits:
        raise NoRoom
    return (later or fits)[0]


def _first_index(usable: list[date], cursor: int, entry: Entry) -> int:
    """The first usable day rank for `entry`: never before the cursor or its date."""
    floor = entry.not_before
    while floor is not None and cursor < len(usable) and usable[cursor] < floor:
        cursor += 1
    return cursor


def pack_week(
    carried: list[Entry],
    own: list[Entry],
    budget: Budget,
    start: date,
    *,
    completed_kinds: Set[TaskType] = frozenset(),
) -> WeekPacking:
    """Places `carried` (carried over) then `own` (the week's own) over seven days from `start`.

    The tasks are carried in order. The reserved quiz closes the week.
    A practice or a quiz already done can satisfy its rule without reserving a second task.
    """
    days = week_days(start)
    remaining = {day: budget.day_capacity(day) for day in days}
    quiz = None if "quiz" in completed_kinds else final_quiz(own)
    practice = None if "practice" in completed_kinds else first_practice(own)
    reserved = [entry for entry in (quiz, practice) if entry is not None]
    reserve = sum(entry.task.minutes for entry in reserved)
    if reserve > budget.cap_minutes:
        raise NoRoom
    last_day = days[-1]
    placed: list[Placement] = []
    if quiz is not None:
        last_day = _quiz_day(days, remaining, quiz.task.minutes)
        remaining[last_day] -= quiz.task.minutes
        placed.append(Placement(quiz, last_day, final_quiz=True))
    usable = [day for day in days if day <= last_day]
    if practice is not None:
        day = _practice_day(usable, remaining, practice)
        remaining[day] -= practice.task.minutes
        placed.append(Placement(practice, day))
    queue = carried + [entry for entry in own if entry not in reserved]
    deferred: list[Entry] = []
    charge, cursor = 0, 0
    for entry in queue:
        minutes = entry.task.minutes
        first = _first_index(usable, cursor, entry)
        index = next(
            (i for i in range(first, len(usable)) if remaining[usable[i]] >= minutes), None
        )
        if deferred or index is None or charge + minutes > budget.cap_minutes - reserve:
            deferred.append(entry)
            continue
        remaining[usable[index]] -= minutes
        charge += minutes
        cursor = index
        placed.append(Placement(entry, usable[index]))
    placed.sort(key=lambda p: (p.day, p.final_quiz, p.entry.origin))
    return WeekPacking(placed, deferred)


@dataclass(frozen=True)
class ScheduledTask:
    title: str
    type: TaskType
    minutes: int
    done_criterion: str
    planned_date: date
    already_known: bool
    module_index: int


@dataclass(frozen=True)
class ScheduledWeek:
    rank: int
    theme: str
    objective: str
    deliverable: str
    start_date: date
    modules: list[ModuleDraft]
    tasks: list[ScheduledTask]
    load_minutes: int
    stage: str | None = None
    rationale: str | None = None


@dataclass(frozen=True)
class ScheduledPlan:
    weeks: list[ScheduledWeek]
    skipped_modules: list[str]
    moved_tasks: int


def _reserved(tasks: list[ScheduledTask]) -> set[int]:
    """Ranks of the quiz that closes the week (the last) and of its first practice."""
    quizzes = [i for i, task in enumerate(tasks) if task.type == "quiz"]
    practices = [i for i, task in enumerate(tasks) if task.type == "practice"]
    return set(quizzes[-1:] + practices[:1])


def _slots(week: ScheduledWeek) -> WeekSlots:
    reserved = _reserved(week.tasks)
    return WeekSlots(
        week.start_date,
        [Dated(t.minutes, t.planned_date, i in reserved) for i, t in enumerate(week.tasks)],
    )


def _module_slot(modules: list[ModuleDraft], source: ModuleDraft) -> int:
    """Rank, in `modules`, of the original module of a pulled-forward task: the same module (title
    without " (continued)", same skills) if it is there, otherwise added under its title followed
    by " (continued)"."""
    base = strip_suite_suffix(source.title)
    for index, module in enumerate(modules):
        if source.chapter_index is not None:
            if module.chapter_index == source.chapter_index:
                return index
            continue
        if (
            module.chapter_index is None
            and strip_suite_suffix(module.title) == base
            and module.skills == source.skills
        ):
            return index
    modules.append(source.model_copy(update={"title": f"{base[:112]}{SUITE_SUFFIX}"}))
    return len(modules) - 1


def _draft(task: ScheduledTask) -> TaskDraft:
    return TaskDraft.model_construct(
        title=task.title, type=task.type, minutes=task.minutes, done_criterion=task.done_criterion
    )


def _rebuilt(
    week: ScheduledWeek, modules: list[ModuleDraft], tasks: list[ScheduledTask]
) -> ScheduledWeek:
    """The week with these tasks: emptied modules removed, module ranks recomputed."""
    used = sorted({task.module_index for task in tasks})
    rank = {old: new for new, old in enumerate(used)}
    tasks = [replace(task, module_index=rank[task.module_index]) for task in tasks]
    kept = [
        modules[old].model_copy(
            update={"tasks": [_draft(t) for t in tasks if t.module_index == rank[old]]}
        )
        for old in used
    ]
    return replace(week, modules=kept, tasks=tasks, load_minutes=sum(t.minutes for t in tasks))


def _move(
    receiver: ScheduledWeek, source: ScheduledWeek, days: dict[int, date]
) -> tuple[ScheduledWeek, ScheduledWeek]:
    """The tasks `days` (rank in `source` → day) move into `receiver`, before its quiz."""
    modules = list(receiver.modules)
    added = [
        replace(
            source.tasks[index],
            planned_date=day,
            module_index=_module_slot(modules, source.modules[source.tasks[index].module_index]),
        )
        for index, day in sorted(days.items())
    ]
    closing = receiver.tasks[-1] if receiver.tasks and receiver.tasks[-1].type == "quiz" else None
    tasks = sorted([*receiver.tasks, *added], key=lambda t: (t.planned_date, t is closing))
    staying = [task for index, task in enumerate(source.tasks) if index not in days]
    return _rebuilt(receiver, modules, tasks), _rebuilt(source, list(source.modules), staying)


def pull_forward(
    weeks: list[ScheduledWeek], budget: Budget, *, floor_share: float
) -> list[ScheduledWeek]:
    """Each week (except the last) under `floor_share` × cap pulls forward, in order, tasks of
    the next one (never its quiz or its reserved practice) onto its days that have room,
    without exceeding the cap (`advance.plan_advances`). A pulled-forward task keeps its module,
    added to the week that receives it. Returns new weeks; `weeks` is unchanged."""
    moves = plan_advances([_slots(week) for week in weeks], budget, floor_share=floor_share)
    by_source: dict[int, dict[int, date]] = {}
    for move in moves:
        by_source.setdefault(move.source, {})[move.index] = move.day
    result = list(weeks)
    for source, days in sorted(by_source.items()):
        result[source - 1], result[source] = _move(result[source - 1], result[source], days)
    return result
