from datetime import date, timedelta

import pytest

from app.agents.tools.plan_schema import TaskDraft
from app.db.models.program import TaskType
from app.features.program.service.budget import Budget
from app.features.program.service.packing import (
    Entry,
    NoRoom,
    ScheduledTask,
    ScheduledWeek,
    pack_week,
    pull_forward,
)
from tests.support.program import MONDAY, module, task


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


# --- Avance des tâches dans une semaine trop légère (D98) ----------------------------------------

type Spec = tuple[str, TaskType, int, int, int]  # titre, type, minutes, jour (0 = lundi), module


def _week(rank: int, specs: list[Spec], modules: tuple[str, ...] = ("A",)) -> ScheduledWeek:
    start = MONDAY + timedelta(days=7 * (rank - 1))
    tasks = [
        ScheduledTask(title, kind, minutes, "Notes prises", start + timedelta(days=day), False, m)
        for title, kind, minutes, day, m in specs
    ]
    drafts = [
        module(
            f"Module {name}",
            [task(t.title, t.type, t.minutes) for t in tasks if t.module_index == i],
        )
        for i, name in enumerate(modules)
    ]
    return ScheduledWeek(
        rank,
        f"Thème {rank}",
        "Savoir",
        "Un dépôt",
        start,
        drafts,
        tasks,
        sum(t.minutes for t in tasks),
    )


def _light() -> ScheduledWeek:
    return _week(
        1,
        [
            ("Lire 0", "lire", 30, 0, 0),
            ("Pratiquer 1", "pratiquer", 45, 0, 0),
            ("Quiz 1", "quiz", 20, 5, 0),
        ],
    )


def _full(rank: int = 2) -> ScheduledWeek:
    reads: list[Spec] = [(f"Lire {rank}.{i}", "lire", 120, i, 0) for i in range(1, 5)]
    return _week(
        rank, [("Pratiquer 2", "pratiquer", 45, 0, 0), *reads, ("Quiz 2", "quiz", 20, 5, 0)], ("B",)
    )


def _titles_of(w: ScheduledWeek) -> list[str]:
    return [t.title for t in w.tasks]


def _assert_rules(w: ScheduledWeek, budget: Budget) -> None:
    per_day: dict[date, int] = {}
    for t in w.tasks:
        per_day[t.planned_date] = per_day.get(t.planned_date, 0) + t.minutes
        assert w.start_date <= t.planned_date <= w.tasks[-1].planned_date
        assert 0 <= t.module_index < len(w.modules)
    assert all(m <= budget.day_capacity(d) for d, m in per_day.items())
    assert w.load_minutes == sum(per_day.values()) <= budget.cap_minutes
    assert w.tasks[-1].type == "quiz" and any(t.type == "pratiquer" for t in w.tasks)


def test_pull_forward_fills_a_light_week_up_to_the_floor(budget: Budget) -> None:
    first, second = pull_forward([_light(), _full()], budget, floor_share=0.6)
    assert _titles_of(first) == [
        "Lire 0",
        "Pratiquer 1",
        "Lire 2.1",
        "Lire 2.2",
        "Lire 2.3",
        "Quiz 1",
    ]
    assert first.load_minutes == 455 and second.load_minutes == 185
    assert _titles_of(second) == ["Pratiquer 2", "Lire 2.4", "Quiz 2"]
    assert [m.title for m in first.modules] == ["Module A", "Module B (suite)"]
    assert [t.title for t in first.modules[1].tasks] == ["Lire 2.1", "Lire 2.2", "Lire 2.3"]
    for w in (first, second):
        _assert_rules(w, budget)


def test_pull_forward_never_moves_the_quiz_or_the_reserved_practice(budget: Budget) -> None:
    bare = _week(2, [("Pratiquer 2", "pratiquer", 45, 0, 0), ("Quiz 2", "quiz", 20, 5, 0)])
    first, second = pull_forward([_light(), bare], budget, floor_share=1.0)
    assert first == _light() and second == bare


def test_pull_forward_leaves_full_weeks_and_the_last_week(budget: Budget) -> None:
    weeks = [_full(1), _full(2), _light()]
    assert pull_forward(weeks, budget, floor_share=0.6) == weeks
    assert pull_forward([_light()], budget, floor_share=0.6) == [_light()]


def test_full_share_fills_up_to_the_cap_in_order(budget: Budget) -> None:
    first, second = pull_forward([_light(), _full(), _full(3)], budget, floor_share=1.0)[:2]
    assert _titles_of(first)[2:-1] == ["Lire 2.1", "Lire 2.2", "Lire 2.3", "Lire 2.4"]
    assert first.load_minutes == 575 and _titles_of(second)[1:3] == ["Lire 3.1", "Lire 3.2"]
    for w in (first, second):
        _assert_rules(w, budget)


def test_emptied_module_leaves_its_week(budget: Budget) -> None:
    specs: list[Spec] = [
        ("Lire seul", "lire", 60, 0, 0),
        ("Pratiquer 2", "pratiquer", 45, 0, 1),
        ("Lire 2.1", "lire", 120, 1, 1),
        ("Quiz 2", "quiz", 20, 5, 1),
    ]
    first, second = pull_forward([_light(), _week(2, specs, ("X", "Y"))], budget, floor_share=0.6)
    assert [m.title for m in first.modules] == ["Module A", "Module X (suite)", "Module Y (suite)"]
    assert [m.title for m in second.modules] == ["Module Y"]
    assert all(t.module_index == 0 for t in second.tasks)
    for w in (first, second):
        _assert_rules(w, budget)


def test_pull_forward_does_not_change_its_input(budget: Budget) -> None:
    weeks = [_light(), _full()]
    pull_forward(weeks, budget, floor_share=0.6)
    assert weeks == [_light(), _full()]


def test_same_module_in_the_receiving_week_is_reused(budget: Budget) -> None:
    same = _week(2, [("Pratiquer 2", "pratiquer", 45, 0, 0), ("Lire 2.1", "lire", 120, 1, 0),
                     ("Quiz 2", "quiz", 20, 5, 0)])  # fmt: skip
    first, _ = pull_forward([_light(), same], budget, floor_share=0.6)
    assert [m.title for m in first.modules] == ["Module A"]
    assert [t.title for t in first.modules[0].tasks] == [
        "Lire 0",
        "Pratiquer 1",
        "Lire 2.1",
        "Quiz 1",
    ]
