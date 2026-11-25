"""Advancing tasks in a light week (D98), on a minimal shared type: dated tasks (minutes, day,
booking). Packing a draft (`packing.pull_forward`, 60% of the cap) and replanning on database
rows ("advance", 100%) use it; each then applies the moves to its own data. Pure functions."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from app.features.program.service.budget import Budget
from app.features.program.service.rules import floor_minutes


@dataclass(frozen=True)
class Dated:
    """A packed task. `reserved`: the quiz that closes its week or its reserved practice, never
    advanced."""

    minutes: int
    day: date
    reserved: bool = False


@dataclass(frozen=True)
class WeekSlots:
    start: date
    tasks: Sequence[Dated]


@dataclass(frozen=True)
class Advance:
    """The `index` task of week `source` moves to day `day` of week `source - 1`."""

    source: int
    index: int
    day: date


@dataclass
class _Receiver:
    """Receiving week: load, minutes per day, cursor (never before the last non-reserved task: the
    chapter order is kept) and last day (that of the quiz)."""

    load: int
    used: dict[date, int]
    cursor: date
    last_day: date

    @classmethod
    def of(cls, week: WeekSlots, kept: Sequence[Dated]) -> "_Receiver":
        used: dict[date, int] = {}
        for task in kept:
            used[task.day] = used.get(task.day, 0) + task.minutes
        free = [task.day for task in kept if not task.reserved]
        last = max((task.day for task in kept), default=week.start + timedelta(days=6))
        return cls(sum(used.values()), used, max(free, default=week.start), last)

    def place(self, task: Dated, budget: Budget) -> date | None:
        """The first day, from the cursor, that has room for `task` without exceeding the cap."""
        if self.load + task.minutes > budget.cap_minutes:
            return None
        day = self.cursor
        while day <= self.last_day:
            if budget.day_capacity(day) - self.used.get(day, 0) >= task.minutes:
                self.used[day] = self.used.get(day, 0) + task.minutes
                self.load += task.minutes
                self.cursor = day
                return day
            day += timedelta(days=1)
        return None


def plan_advances(
    weeks: Sequence[WeekSlots], budget: Budget, *, floor_share: float
) -> list[Advance]:
    """For each week (except the last) below `floor_share` × cap, in order: advances the next week's
    tasks, in their order and never a reserved one, on the days that have room and up to the quiz
    day, without exceeding the cap, as long as the week stays under the threshold; the first one
    that does not fit stops the advance. An emptied week may in turn advance tasks from the
    following one."""
    floor = floor_minutes(budget.cap_minutes, floor_share)
    left: list[list[tuple[int, Dated]]] = [list(enumerate(w.tasks)) for w in weeks]
    moves: list[Advance] = []
    for index in range(len(weeks) - 1):
        receiver = _Receiver.of(weeks[index], [task for _, task in left[index]])
        moved: set[int] = set()
        for rank, task in left[index + 1]:
            if receiver.load >= floor:
                break
            if task.reserved:
                continue
            day = receiver.place(task, budget)
            if day is None:
                break
            moves.append(Advance(index + 1, rank, day))
            moved.add(rank)
        left[index + 1] = [(rank, task) for rank, task in left[index + 1] if rank not in moved]
    return moves
