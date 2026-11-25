"""Replanning on the program's rows (SPEC F13, D106): rows fingerprint and packing of a
proposal (`repack`). Pure functions, without a database or model.

Only the tasks to do move, from the current week and the following ones; a task keeps its
module, only its date changes (D88 §1: a task's week is that of its day). The budget comes
before the deadline: what does not fit goes into "Continued" weeks, whatever the option. The
packing is stable (final review of phase 5, P-I1): a week that receives neither delay nor
addition keeps its dates (`replan_stable.keeps_dates`), and a task to do is never placed
before its date, except with the "pull forward" option, which never pulls forward a "Retake
the quiz". "Push back the deadline" packs the coming weeks under 60% of the cap (P-I2): the
surplus goes into "Continued" weeks, the deadline moves back. Writing is in `replan_versions`."""

import hashlib
import json
from collections.abc import Sequence, Set
from dataclasses import dataclass
from datetime import date, timedelta

from app.agents.tools.plan_schema import TaskDraft
from app.agents.tools.replan_port import WeekLoad
from app.agents.tools.study_schema import ReplanOption
from app.core.clock import week_start
from app.features.program.service.budget import Budget
from app.features.program.service.diff import ProgramRows, TaskRow
from app.features.program.service.packing import Entry, NoRoom, WeekPacking, pack_week
from app.features.program.service.planning import (
    PlanningImpossible,
)
from app.features.program.service.replan_rows import (
    NewTask,
    NewWeek,
    PlannedTask,
    Slots,
    WeekBudget,
    open_week,
    week_budget,
    week_loads,
)
from app.features.program.service.replan_stable import advance, keeps_dates
from app.features.program.service.rules import is_retry

__all__ = ["NewTask", "NewWeek", "PlannedTask", "RepackResult", "fingerprint", "repack"]

DAYS = 7


class ProgramFinished(PlanningImpossible):
    """No week left to replan: the program is finished."""

    def __init__(self) -> None:
        super().__init__("The program is finished: no week left to replan.")


def fingerprint(rows: ProgramRows) -> str:
    """sha256 of the sorted `(task, day, status, minutes)`: any edit by January (day, duration,
    ticked box, addition, removal) changes the fingerprint."""
    items = sorted(
        (t.task_id, t.planned_date.isoformat(), t.status, t.minutes)
        for week in rows.weeks
        for module in week.modules
        for t in module.tasks
    )
    return hashlib.sha256(json.dumps(items).encode()).hexdigest()


@dataclass(frozen=True)
class RepackResult:
    """`tasks`: all the tasks to do after packing (kept, added, and practice and quiz of the
    "Continued" weeks); `removed`: ids removed; `kept`: removals ignored (last quiz or last
    practice of a week)."""

    tasks: list[PlannedTask]
    new_weeks: list[NewWeek]
    loads: list[WeekLoad]
    deadline_moved: bool
    removed: list[str]
    kept: int


@dataclass(frozen=True)
class _Row:
    task: TaskRow
    module_id: str


def _rows(rows: ProgramRows) -> list[_Row]:
    """The tasks in the program's order (week, module, rank), then by date."""
    found = [_Row(t, m.module_id) for week in rows.weeks for m in week.modules for t in m.tasks]
    order = {id(r): n for n, r in enumerate(found)}
    return sorted(found, key=lambda r: (r.task.planned_date, order[id(r)]))


def _start_day(today: date, budget: Budget) -> date:
    """Today, or next Monday if no working day is left this week (the Sunday review replans
    from the following week)."""
    monday = week_start(today)
    left = (today + timedelta(days=n) for n in range((monday + timedelta(days=6) - today).days + 1))
    return today if any(budget.day_capacity(day) > 0 for day in left) else monday + timedelta(DAYS)


def _span(starts: Sequence[date], day: date) -> int:
    """The rank of the week whose seven days contain `day` (before the first: 0)."""
    for index, start in enumerate(starts):
        if day < start + timedelta(days=DAYS):
            return index
    return len(starts)


def _drops(found: list[_Row], starts: list[date], drop: Set[str]) -> tuple[set[str], int]:
    """The removals made, and those ignored: never the last quiz nor the last practice of its
    week (done ones included)."""
    removed: set[str] = set()
    kept = 0
    for row in found:
        task = row.task
        if task.task_id not in drop or task.status != "todo":
            continue
        week = _span(starts, task.planned_date)
        same = [
            r
            for r in found
            if r.task.type == task.type
            and _span(starts, r.task.planned_date) == week
            and r.task.task_id not in removed
        ]
        if task.type in ("practice", "quiz") and len(same) == 1:
            kept += 1
            continue
        removed.add(task.task_id)
    return removed, kept


def _planned(row: _Row) -> PlannedTask:
    t = row.task
    return PlannedTask(
        t.task_id, t.planned_date, t.title, t.type, t.minutes, t.done_criterion, row.module_id
    )


def _entry(task: PlannedTask, seq: int) -> Entry:
    """An existing task is never placed before its date (`not_before`); a "Retake the quiz"
    never closes the week in place of its quiz."""
    draft = TaskDraft.model_construct(
        title=task.title, type=task.type, minutes=task.minutes, done_criterion=task.done_criterion
    )
    floor = task.planned_date if task.task_id else None
    return Entry(draft, (seq, 0, 0), floor, is_retry(task.title, task.type))


@dataclass
class _Queue:
    """The tasks to pack, numbered in queue order (`origin` of the entries)."""

    tasks: list[PlannedTask]

    def entries(self, items: Sequence[PlannedTask]) -> list[Entry]:
        out = []
        for item in items:
            self.tasks.append(item)
            out.append(_entry(item, len(self.tasks) - 1))
        return out


def _own(
    rows: ProgramRows, found: list[_Row], current: int, removed: set[str], add: Sequence[NewTask]
) -> tuple[list[PlannedTask], dict[int, list[PlannedTask]]]:
    """The delays of past weeks, then the tasks to do of each week; a Strategist addition goes
    to the end of its module's week (even empty: "Postings skills", D123) if it is current or
    upcoming, otherwise of the current week."""
    starts = [week.start_date for week in rows.weeks]
    late: list[PlannedTask] = []
    own: dict[int, list[PlannedTask]] = {}
    for row in found:
        if row.task.status != "todo" or row.task.task_id in removed:
            continue
        week = _span(starts, row.task.planned_date)
        (late if week < current else own.setdefault(week, [])).append(_planned(row))
    weeks = {m.module_id: index for index, week in enumerate(rows.weeks) for m in week.modules}
    for new in add:
        week = max(weeks.get(new.module_id, current), current)
        day = starts[week] if week < len(starts) else starts[-1]
        own.setdefault(week, []).append(
            PlannedTask(
                "", day, new.title, new.type, new.minutes, new.done_criterion, new.module_id
            )
        )
    return late, own


def _done_minutes(found: list[_Row]) -> dict[date, int]:
    used: dict[date, int] = {}
    for row in found:
        if row.task.status == "done":
            used[row.task.planned_date] = used.get(row.task.planned_date, 0) + row.task.minutes
    return used


def _cap(
    budget: Budget, current: bool, override: int | None, option: ReplanOption | None
) -> tuple[int, bool]:
    """The week's cap (January's for the current week, if given), and whether it must be
    lowered ("Push back the deadline", any other week)."""
    if current and override is not None:
        return override, False
    return budget.cap_minutes, option == "push_deadline"


def _pack(
    carried: list[Entry], mine: list[Entry], week: WeekBudget, start: date, found: list[_Row]
) -> WeekPacking:
    try:
        return pack_week(carried, mine, week, start)
    except NoRoom:
        end = start + timedelta(days=DAYS)
        completed = {
            row.task.type
            for row in found
            if row.task.status == "done"
            and start <= row.task.planned_date < end
            and row.task.type in ("practice", "quiz")
        }
    if not completed:
        raise PlanningImpossible()
    try:
        return pack_week(carried, mine, week, start, completed_kinds=completed)
    except NoRoom:
        raise PlanningImpossible() from None


def _kept(queue: _Queue, tasks: list[PlannedTask]) -> list[tuple[int, date]]:
    """A week kept as it is: each task on its date."""
    entries = queue.entries(tasks)
    return [(e.origin[0], t.planned_date) for e, t in zip(entries, tasks, strict=True)]


def repack(
    rows: ProgramRows,
    budget: Budget,
    *,
    today: date,
    drop: Set[str],
    add: Sequence[NewTask],
    option: ReplanOption | None,
    week_cap_override: int | None,
) -> RepackResult:
    """Packs the rest of the program (see the module); `PlanningImpossible` if a week cannot
    hold its practice and quiz, or if the program is finished."""
    starts = [week.start_date for week in rows.weeks]
    found = _rows(rows)
    from_day = _start_day(today, budget)
    current = _span(starts, from_day)
    if current >= len(starts):
        raise ProgramFinished()
    removed, kept = _drops(found, starts, drop)
    late, own = _own(rows, found, current, removed, add)
    used = _done_minutes(found)
    queue = _Queue([])
    carried = queue.entries(late)
    placed: list[tuple[int, date]] = []  # (rank in the queue, day)
    new_weeks: list[NewWeek] = []
    index = current
    while index < len(starts) or carried:
        start = open_week(rows, index, new_weeks, own)
        cap, lower = _cap(budget, index == current, week_cap_override, option)
        week = week_budget(budget, cap, used, start, from_day, lower=lower)
        if not carried and keeps_dates(own.get(index, []), week, start):
            placed += _kept(queue, own.get(index, []))  # no delay or addition: dates kept
            index += 1
            continue
        mine = queue.entries(own.get(index, []))
        packing = _pack(carried, mine, week, start, found)
        if index >= len(starts) and not any(p.entry not in mine for p in packing.placed):
            raise PlanningImpossible()
        placed += [(p.entry.origin[0], p.day) for p in packing.placed]
        carried = packing.deferred
        index += 1
    tasks = [queue.tasks[seq].moved(day) for seq, day in sorted(placed)]
    slots = Slots(starts + [w.start_date for w in new_weeks], current, found, budget, from_day)
    if option == "advance":
        tasks = advance(tasks, slots, skip_current=week_cap_override is not None)
    loads = week_loads(slots, tasks, week_cap_override)
    return RepackResult(tasks, new_weeks, loads, bool(new_weeks), sorted(removed), kept)
