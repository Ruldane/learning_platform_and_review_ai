"""Rangement d'une replanification sur les lignes (D106) : retards redistribués sous le plafond,
plafond de January (255 pour 5 heures), semaines « Suite », tâches faites et passées figées,
« avancer », retraits gardés, empreinte. Fonctions pures, sans base."""

from dataclasses import replace
from datetime import date, timedelta

import pytest

from app.agents.tools.replan_port import week_cap
from app.db.models.program import TaskType
from app.features.program.service.budget import Budget
from app.features.program.service.diff import ModuleRow, ProgramRows, TaskRow, WeekRow
from app.features.program.service.planning import PlanningImpossible
from app.features.program.service.replan_rows import PlannedTask, after_rows
from app.features.program.service.replanning import RepackResult, fingerprint, repack

BUDGET = Budget(120, 240)  # 840 par semaine, plafond 714
W1, W2, W3 = date(2026, 11, 9), date(2026, 11, 16), date(2026, 11, 23)
TUESDAY = date(2026, 11, 17)  # semaine 2


def t(task_id: str, kind: TaskType, minutes: int, day: date, status: str = "todo") -> TaskRow:
    return TaskRow(task_id, kind, minutes, day, task_id=task_id, status=status)


def week(rank: int, start: date, tasks: list[TaskRow]) -> WeekRow:
    module = ModuleRow(f"Module {rank}", tasks=tasks, module_id=f"module-{rank}")
    return WeekRow(rank, f"Thème {rank}", start, [module], "Objectif", "Livrable")


def d(start: date, offset: int) -> date:
    return start + timedelta(days=offset)


def first_week() -> WeekRow:
    """Deux lectures faites, deux en retard, pratique et quiz faits."""
    return week(
        1,
        W1,
        [
            t("w1-r1", "lire", 120, d(W1, 0), "done"),
            t("w1-r2", "lire", 120, d(W1, 1), "done"),
            t("w1-r3", "lire", 120, d(W1, 2)),
            t("w1-r4", "lire", 120, d(W1, 3)),
            t("w1-p", "pratiquer", 45, d(W1, 4), "done"),
            t("w1-q", "quiz", 20, d(W1, 5), "done"),
        ],
    )


def second_week() -> WeekRow:
    reads = [t(f"w2-r{n}", "lire", 120, d(W2, n)) for n in range(4)]
    return week(
        2, W2, [*reads, t("w2-p", "pratiquer", 45, d(W2, 4)), t("w2-q", "quiz", 20, d(W2, 5))]
    )


def third_week(reads: int = 2, minutes: int = 60) -> WeekRow:
    tasks = [t(f"w3-r{n}", "lire", minutes, d(W3, n)) for n in range(reads)]
    return week(
        3, W3, [*tasks, t("w3-p", "pratiquer", 45, d(W3, 4)), t("w3-q", "quiz", 20, d(W3, 5))]
    )


def plan(third: WeekRow | None = None) -> ProgramRows:
    return ProgramRows([first_week(), second_week(), third or third_week()])


def run(rows: ProgramRows, **over: object) -> RepackResult:
    args: dict[str, object] = {
        "today": TUESDAY,
        "drop": set(),
        "add": [],
        "option": None,
        "week_cap_override": None,
    }
    args.update(over)
    return repack(rows, BUDGET, **args)  # type: ignore[arg-type]


def in_week(tasks: list[PlannedTask], start: date) -> list[PlannedTask]:
    return [x for x in tasks if start <= x.planned_date < start + timedelta(days=7)]


def test_repack_redistributes_late_tasks_within_cap() -> None:
    result = run(plan())
    assert [w.rank for w in result.loads] == [2, 3]
    assert all(w.after <= w.cap == 714 for w in result.loads)
    assert all(x.planned_date >= TUESDAY for x in result.tasks)  # rien sur un jour passé
    moved = {x.task_id: x.planned_date for x in result.tasks}
    assert W2 <= moved["w1-r3"] < W3 and W2 <= moved["w1-r4"] < W3  # retards en tête
    for start in (W2, W3):
        tasks = in_week(result.tasks, start)
        quiz = next(x for x in tasks if x.type == "quiz")
        assert all(x.planned_date <= quiz.planned_date for x in tasks)  # le quiz ferme
    assert not result.deadline_moved and result.removed == [] and result.kept == 0


def test_repack_with_week_override_respects_255() -> None:
    result = run(plan(), week_cap_override=week_cap(300))
    current = result.loads[0]
    assert (current.rank, current.cap) == (2, 255) and current.after <= 255
    assert result.loads[1].cap == 714 and result.loads[1].after <= 714
    kinds = {x.type for x in in_week(result.tasks, W2)}
    assert {"pratiquer", "quiz"} <= kinds  # la semaine garde sa pratique et son quiz


def test_repack_overflow_appends_suite_week() -> None:
    result = run(plan(third_week(reads=5, minutes=120)))
    assert result.deadline_moved
    new = result.new_weeks[0]
    assert (new.rank, new.start_date, new.theme) == (4, date(2026, 11, 30), "Suite : Thème 3")
    suite = [x for x in result.tasks if x.suite_rank == 4]
    assert sorted(x.type for x in suite) == ["pratiquer", "quiz"]
    assert [w.rank for w in result.loads] == [2, 3, 4]
    assert all(w.after <= w.cap for w in result.loads)
    after = after_rows(plan(third_week(5, 120)), result.tasks, result.removed, result.new_weeks)
    assert [w.theme for w in after.weeks][-1] == "Suite : Thème 3"


def test_repack_keeps_done_and_past_tasks() -> None:
    rows = plan()
    result = run(rows)
    ids = {x.task_id for x in result.tasks}
    assert not ids & {"w1-r1", "w1-r2", "w1-p", "w1-q"}  # faites : jamais touchées
    after = after_rows(rows, result.tasks, result.removed, result.new_weeks)
    done = {x.task_id: x.planned_date for w in after.weeks for m in w.modules for x in m.tasks}
    assert done["w1-r1"] == d(W1, 0) and done["w1-q"] == d(W1, 5)
    # La tâche garde son module : seule sa date change (D88 §1, F5).
    first = after.weeks[0].modules[0]
    assert {x.task_id for x in first.tasks} == {x.task_id for x in rows.weeks[0].modules[0].tasks}


def test_advance_pulls_next_week_into_current() -> None:
    light = week(
        2,
        W2,
        [
            t("w2-r", "lire", 60, d(W2, 1)),
            t("w2-p", "pratiquer", 45, d(W2, 2)),
            t("w2-q", "quiz", 20, d(W2, 5)),
        ],
    )
    rows = ProgramRows([first_week(), light, third_week(reads=3, minutes=120)])
    done_w1 = [replace(x, status="done") for x in rows.weeks[0].modules[0].tasks]
    rows.weeks[0] = replace(
        rows.weeks[0], modules=[replace(rows.weeks[0].modules[0], tasks=done_w1)]
    )
    plain = run(rows)
    ahead = run(rows, option="advance")
    assert len(in_week(ahead.tasks, W2)) > len(in_week(plain.tasks, W2))
    pulled = [x for x in in_week(ahead.tasks, W2) if x.task_id.startswith("w3-r")]
    assert pulled and all(w.after <= w.cap for w in ahead.loads)
    assert {x.task_id for x in in_week(ahead.tasks, W3)} >= {"w3-p", "w3-q"}  # réservées


def test_drop_never_removes_last_quiz_or_practice() -> None:
    result = run(plan(), drop={"w2-q", "w2-p", "w2-r3"}, option="reduce_scope")
    assert result.removed == ["w2-r3"] and result.kept == 2
    assert {"w2-q", "w2-p"} <= {x.task_id for x in result.tasks}


def test_sunday_review_replans_from_next_monday() -> None:
    sunday = date(2026, 11, 22)
    result = run(plan(), today=sunday)
    assert result.loads[0].rank == 3  # rien ne reste au dimanche (jour libre)
    assert all(x.planned_date >= W3 for x in result.tasks)
    assert result.deadline_moved and all(w.after <= w.cap for w in result.loads)


def test_too_small_cap_or_finished_program_is_impossible() -> None:
    with pytest.raises(PlanningImpossible):
        run(plan(), week_cap_override=week_cap(60))  # 51 min : ni pratique ni quiz
    with pytest.raises(PlanningImpossible):
        run(plan(), today=date(2026, 12, 7))


def test_fingerprint_sees_dates_status_and_minutes() -> None:
    rows = plan()
    base = fingerprint(rows)
    assert fingerprint(plan()) == base
    moved = replace(rows.weeks[1].modules[0].tasks[0], planned_date=d(W2, 2))
    tasks = [moved, *rows.weeks[1].modules[0].tasks[1:]]
    changed = ProgramRows(
        [
            rows.weeks[0],
            replace(rows.weeks[1], modules=[ModuleRow("M", tasks=tasks)]),
            rows.weeks[2],
        ]
    )
    assert fingerprint(changed) != base
