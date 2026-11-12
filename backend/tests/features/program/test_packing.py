from datetime import date

import pytest

from app.agents.tools.plan_schema import TaskDraft
from app.db.models.program import TaskType
from app.features.program.service.budget import Budget
from app.features.program.service.packing import Entry, NoRoom, pack_week
from tests.support.program import MONDAY, task


def _entries(specs: list[tuple[str, TaskType, int]], week: int = 0) -> list[Entry]:
    return [
        Entry(task(title, kind, minutes), (week, 0, i))
        for i, (title, kind, minutes) in enumerate(specs)
    ]


def _own(reads: list[int]) -> list[Entry]:
    specs: list[tuple[str, TaskType, int]] = [(f"Lire {i}", "lire", m) for i, m in enumerate(reads)]
    return _entries([*specs, ("Pratiquer", "pratiquer", 45), ("Quiz", "quiz", 20)])


def _titles(entries: list[Entry]) -> list[str]:
    return [e.task.title for e in entries]


def test_light_week_fits_and_quiz_closes_saturday(budget: Budget) -> None:
    packing = pack_week([], _own([30, 30, 30]), budget, MONDAY)
    assert packing.deferred == []
    last = packing.placed[-1]
    assert last.final_quiz and last.day == date(2026, 11, 21)
    assert all(p.day <= last.day for p in packing.placed)


def test_practice_takes_first_day_with_room(budget: Budget) -> None:
    packing = pack_week([], _own([30]), budget, MONDAY)
    practice = next(p for p in packing.placed if p.entry.task.type == "pratiquer")
    assert practice.day == MONDAY


def test_day_capacity_and_cap_are_respected(budget: Budget) -> None:
    packing = pack_week([], _own([120] * 8), budget, MONDAY)
    per_day: dict[date, int] = {}
    for p in packing.placed:
        per_day[p.day] = per_day.get(p.day, 0) + p.entry.task.minutes
    assert all(m <= budget.day_capacity(d) for d, m in per_day.items())
    assert sum(per_day.values()) <= budget.cap_minutes
    assert _titles(packing.deferred) == ["Lire 5", "Lire 6", "Lire 7"]


def test_after_a_deferral_every_later_task_is_deferred(budget: Budget) -> None:
    packing = pack_week([], _own([120, 120, 120, 120, 120, 120, 15]), budget, MONDAY)
    assert _titles(packing.deferred)[-1] == "Lire 6" and "Lire 5" in _titles(packing.deferred)


def test_carried_tasks_come_first(budget: Budget) -> None:
    carried = _entries([("Reste", "lire", 60)], week=0)
    own = [Entry(e.task, (1, 0, i)) for i, e in enumerate(_own([30]))]
    packing = pack_week(carried, own, budget, MONDAY)
    reads = [p for p in packing.placed if p.entry.task.type == "lire"]
    assert [p.entry.task.title for p in reads] == ["Reste", "Lire 0"]


def test_practice_still_fits_when_days_are_fragmented(budget: Budget) -> None:
    packing = pack_week([], _own([100] * 5), budget, MONDAY)
    assert any(p.entry.task.type == "pratiquer" for p in packing.placed)
    assert packing.deferred == []


def test_nothing_is_placed_on_sunday() -> None:
    wide = Budget(weekday_minutes=120, weekend_minutes=240)
    sunday_start = date(2026, 11, 22)
    packing = pack_week([], _own([30, 30]), wide, sunday_start)
    assert all(p.day.weekday() != 6 for p in packing.placed)


def test_reserve_above_the_cap_has_no_room() -> None:
    with pytest.raises(NoRoom):
        pack_week([], _own([15]), Budget(weekday_minutes=10, weekend_minutes=20), MONDAY)


def test_week_without_practice_or_quiz_reserves_nothing(budget: Budget) -> None:
    only_reads = _entries([("Lire un", "lire", 60), ("Lire deux", "lire", 60)])
    packing = pack_week([], only_reads, budget, MONDAY)
    assert packing.deferred == [] and not any(p.final_quiz for p in packing.placed)


def test_same_task_object_is_not_duplicated(budget: Budget) -> None:
    draft = TaskDraft(title="Lire un", type="lire", minutes=30, done_criterion="Notes prises")
    twin = [Entry(draft, (0, 0, 0)), Entry(draft, (0, 0, 1))]
    packing = pack_week([], twin, budget, MONDAY)
    assert len(packing.placed) == 2
