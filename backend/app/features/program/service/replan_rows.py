"""Pieces of a replanning's packing (`replanning.repack`, D106): placed tasks, "Continued"
weeks, budget of a started week, loads and rules of the touched weeks, and the plan after the
proposal (for the snapshot and the difference). Advancing ("pull forward") and the weeks kept
as they are are in `replan_stable`. Pure functions."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from typing import Any, Protocol

from app.agents.tools.replan_port import WeekLoad
from app.db.models.program import TaskType
from app.features.program.service import rules
from app.features.program.service.budget import Budget
from app.features.program.service.diff import ModuleRow, ProgramRows, TaskRow, WeekRow
from app.features.program.service.planning import (
    MAX_WEEKS,
    PRACTICE_MINUTES,
    QUIZ_MINUTES,
    PlanningImpossible,
)
from app.features.program.service.rules import UNDERLOAD_SHARE, floor_minutes, week_breaks

DAYS = 7
PRACTICE_CRITERION = "Produce a result you can show and explain"
QUIZ_CRITERION = "Answer all the questions then re-read the mistakes"


@dataclass(frozen=True)
class NewTask:
    """A task added by the Strategist ("go deeper") in an existing module."""

    module_id: str
    title: str
    type: TaskType
    minutes: int
    done_criterion: str


@dataclass(frozen=True)
class PlannedTask:
    """A task to do after packing. Empty `task_id`: new task, in `module_id` (Strategist's
    addition) or in the module of the "Continued" week of rank `suite_rank`."""

    task_id: str
    planned_date: date
    title: str
    type: TaskType
    minutes: int
    done_criterion: str
    module_id: str
    suite_rank: int | None = None

    def moved(self, day: date) -> "PlannedTask":
        return replace(self, planned_date=day)

    def to_json(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "planned_date": self.planned_date.isoformat(),
            "title": self.title,
            "type": self.type,
            "minutes": self.minutes,
            "done_criterion": self.done_criterion,
            "module_id": self.module_id,
            "suite_rank": self.suite_rank,
        }

    @classmethod
    def from_json(cls, raw: Mapping[str, Any]) -> "PlannedTask":
        return cls(
            str(raw["task_id"]),
            date.fromisoformat(str(raw["planned_date"])),
            str(raw["title"]),
            raw["type"],
            int(raw["minutes"]),
            str(raw["done_criterion"]),
            str(raw["module_id"]),
            None if raw.get("suite_rank") is None else int(raw["suite_rank"]),
        )


@dataclass(frozen=True)
class NewWeek:
    """A "Continued" week: what does not fit in the budget, rather than an overrun."""

    rank: int
    theme: str
    objective: str
    deliverable: str
    start_date: date

    def to_json(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "theme": self.theme,
            "objective": self.objective,
            "deliverable": self.deliverable,
            "start_date": self.start_date.isoformat(),
        }

    @classmethod
    def from_json(cls, raw: Mapping[str, Any]) -> "NewWeek":
        return cls(
            int(raw["rank"]),
            str(raw["theme"]),
            str(raw["objective"]),
            str(raw["deliverable"]),
            date.fromisoformat(str(raw["start_date"])),
        )


@dataclass(frozen=True)
class WeekBudget(Budget):
    """The budget of a started week: cap (85%, or January's this week) minus the minutes
    already done, past days closed, done minutes removed from their day."""

    cap: int = 0
    used: Mapping[date, int] = field(default_factory=dict)
    from_day: date = date.min

    @property
    def cap_minutes(self) -> int:
        return self.cap

    def day_capacity(self, day: date) -> int:
        if day < self.from_day:
            return 0
        remaining = max(0, self._usual_capacity(day) - self.used.get(day, 0))
        return min(remaining, self.daily_caps.get(day, remaining))


def week_budget(
    budget: Budget, cap: int, used: dict[date, int], start: date, from_day: date, *, lower: bool
) -> WeekBudget:
    """The week's budget, done minutes removed. `lower` ("Push back the deadline"): cap lowered
    to 60%, always keeping room for a practice and a quiz beyond the done minutes, and never
    beyond the cap (85%)."""
    week_used = {d: m for d, m in used.items() if start <= d < start + timedelta(days=DAYS)}
    done = sum(week_used.values())
    if lower:
        room = min(cap, done + PRACTICE_MINUTES + QUIZ_MINUTES)
        cap = max(floor_minutes(cap, UNDERLOAD_SHARE), room)
    return WeekBudget(
        budget.weekday_minutes,
        budget.weekend_minutes,
        max(0, cap - done),
        week_used,
        from_day,
        daily_caps=budget.daily_caps,
    )


def suite_week(last: WeekRow, rank: int, last_start: date, count: int) -> NewWeek:
    """The "Continued" week of rank `rank`, after the last one (`count` weeks); theme, goal and
    deliverable carried over from the last week."""
    return NewWeek(
        rank,
        rules.suite_theme(last.theme)[:200],
        rules.suite_text(last.objective)[:300],
        rules.suite_text(last.deliverable)[:300],
        last_start + timedelta(days=DAYS * (rank - count)),
    )


def suite_tasks(week: NewWeek) -> list[PlannedTask]:
    """The practice and quiz of a "Continued" week (each week keeps its own)."""
    theme = rules.strip_suite_prefix(week.theme)
    day = week.start_date
    return [
        PlannedTask(
            "",
            day,
            f"Pratiquer : {theme}"[:120],
            "practice",
            PRACTICE_MINUTES,
            PRACTICE_CRITERION,
            "",
            week.rank,
        ),
        PlannedTask(
            "",
            day,
            f"Take the week {week.rank} quiz",
            "quiz",
            QUIZ_MINUTES,
            QUIZ_CRITERION,
            "",
            week.rank,
        ),
    ]


def open_week(
    rows: ProgramRows,
    index: int,
    new_weeks: list[NewWeek],
    own: dict[int, list[PlannedTask]],
) -> date:
    """The start of week `index`; beyond the last one, a "Continued" week is opened with its
    practice and quiz (52 weeks at most)."""
    starts = [week.start_date for week in rows.weeks]
    if index >= MAX_WEEKS:
        raise PlanningImpossible("The program exceeds 52 weeks with this budget.")
    if index < len(starts):
        return starts[index]
    new_weeks.append(suite_week(rows.weeks[-1], index + 1, starts[-1], len(starts)))
    own[index] = suite_tasks(new_weeks[-1])
    return new_weeks[-1].start_date


class _Found(Protocol):
    @property
    def task(self) -> TaskRow: ...


@dataclass(frozen=True)
class Slots:
    """The packing's weeks: starts (old ones then "Continued"), rank of the current week, all
    the original tasks, budget and first open day."""

    starts: list[date]
    current: int
    found: Sequence[_Found]
    budget: Budget
    from_day: date

    def within(self, index: int, day: date) -> bool:
        start = self.starts[index]
        return start <= day < start + timedelta(days=DAYS)

    def done(self, index: int) -> list[TaskRow]:
        return [
            f.task
            for f in self.found
            if f.task.status == "done" and self.within(index, f.task.planned_date)
        ]


def week_loads(slots: Slots, tasks: list[PlannedTask], override: int | None) -> list[WeekLoad]:
    """Before and after load of each touched week, and its rules (85% or January's cap, a
    practice, a quiz): a broken rule raises `PlanningImpossible`."""
    loads: list[WeekLoad] = []
    for index in range(slots.current, len(slots.starts)):
        before = sum(
            f.task.minutes for f in slots.found if slots.within(index, f.task.planned_date)
        )
        after: list[tuple[int, TaskType]] = [(t.minutes, t.type) for t in slots.done(index)]
        after += [(t.minutes, t.type) for t in tasks if slots.within(index, t.planned_date)]
        cap = override if index == slots.current and override is not None else None
        cap = cap if cap is not None else slots.budget.cap_minutes
        if week_breaks(after, cap):
            raise PlanningImpossible()
        total = sum(minutes for minutes, _ in after)
        loads.append(WeekLoad(index + 1, slots.starts[index], before, total, cap))
    return loads


def _row(task: PlannedTask) -> TaskRow:
    return TaskRow(
        task.title,
        task.type,
        task.minutes,
        task.planned_date,
        task_id=task.task_id,
        done_criterion=task.done_criterion,
    )


def after_rows(
    rows: ProgramRows,
    tasks: Sequence[PlannedTask],
    removed: Sequence[str],
    weeks: Sequence[NewWeek],
) -> ProgramRows:
    """The program as the proposal would leave it (snapshot and difference)."""
    dates = {t.task_id: t.planned_date for t in tasks if t.task_id}
    gone = set(removed)
    out: list[WeekRow] = []
    for week in rows.weeks:
        modules = []
        for module in week.modules:
            kept = [
                replace(t, planned_date=dates.get(t.task_id, t.planned_date))
                for t in module.tasks
                if t.task_id not in gone
            ]
            kept += [_row(t) for t in tasks if not t.task_id and t.module_id == module.module_id]
            modules.append(replace(module, tasks=kept))
        out.append(replace(week, modules=modules))
    for new in weeks:
        suite = [_row(t) for t in tasks if t.suite_rank == new.rank]
        module = ModuleRow(new.theme, tasks=suite)
        out.append(
            WeekRow(new.rank, new.theme, new.start_date, [module], new.objective, new.deliverable)
        )
    return ProgramRows(out)
