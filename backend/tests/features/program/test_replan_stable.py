"""Rangement stable d'une replanification (revue finale de la phase 5, P-I1) : semaines sans
retard ni ajout gardées telles quelles, aucune tâche placée avant sa date hors « avancer », jamais
un « Refaire le quiz » avant son jour ; « Repousser l'échéance » (P-I2) : semaines à 60 % du
plafond, surplus en semaines « Suite ». Fonctions pures, sans base."""

from dataclasses import replace
from datetime import date

import pytest

from app.features.program.service.diff import ProgramRows, TaskRow, WeekRow, diff_plans, snapshot
from app.features.program.service.replan_rows import after_rows
from app.features.program.service.rules import RETRY_PREFIX, floor_minutes
from tests.features.program.test_replanning import (
    TUESDAY,
    W2,
    W3,
    d,
    first_week,
    plan,
    run,
    second_week,
    t,
    third_week,
    week,
)


def done_first_week() -> WeekRow:
    first = first_week()
    tasks = [replace(x, status="done") for x in first.modules[0].tasks]
    return replace(first, modules=[replace(first.modules[0], tasks=tasks)])


def retry(day: date) -> TaskRow:
    return TaskRow(f"{RETRY_PREFIX}Module 1", "quiz", 20, day, task_id="retry")


def todo_dates(rows: ProgramRows) -> dict[str, date]:
    return {
        x.task_id: x.planned_date
        for w in rows.weeks
        for m in w.modules
        for x in m.tasks
        if x.status == "todo"
    }


def test_hand_moved_task_keeps_its_date_and_on_track_plan_is_empty() -> None:
    """P-I1 a et c : sans retard, la lecture que January a mise au vendredi 27/11 garde sa date,
    rien ne bouge (la proposition du bilan « dans les temps » est vide)."""
    third = third_week()
    moved = [replace(third.modules[0].tasks[0], planned_date=d(W3, 4)), *third.modules[0].tasks[1:]]
    third = replace(third, modules=[replace(third.modules[0], tasks=moved)])
    rows = ProgramRows([done_first_week(), second_week(), third])
    result = run(rows, today=W2)
    assert {x.task_id: x.planned_date for x in result.tasks} == todo_dates(rows)
    after = after_rows(rows, result.tasks, result.removed, result.new_weeks)
    diff = diff_plans(snapshot(rows), snapshot(after))
    assert not (diff.added or diff.removed or diff.moved or result.new_weeks)


def test_late_tasks_never_pull_a_task_before_its_date() -> None:
    """P-I1 a : une semaine qui reçoit des retards est rangée, mais aucune tâche à faire n'y passe
    avant sa date (hors option « avancer »)."""
    rows = plan()
    before = todo_dates(rows)
    result = run(rows)
    for x in result.tasks:
        if x.task_id in before and before[x.task_id] >= W2:  # ni retard ni jour passé
            assert x.planned_date >= max(before[x.task_id], TUESDAY), x.task_id
    assert all(w.after <= w.cap for w in result.loads)


@pytest.mark.parametrize("late", [False, True])
def test_retry_quiz_is_never_before_its_day(late: bool) -> None:
    """P-I1 b : « Refaire le quiz », posé jeudi (J+2), n'est jamais avancé par le rangement."""
    first = first_week() if late else done_first_week()
    second = week(
        2,
        W2,
        [
            t("w2-r", "lire", 60, d(W2, 1)),
            retry(d(W2, 3)),
            t("w2-p", "pratiquer", 45, d(W2, 4)),
            t("w2-q", "quiz", 20, d(W2, 5)),
        ],
    )
    result = run(ProgramRows([first, second, third_week()]))
    dates = {x.task_id: x.planned_date for x in result.tasks}
    assert dates["retry"] >= d(W2, 3)
    assert all(w.after <= w.cap for w in result.loads)


def test_advance_never_pulls_a_retry_quiz() -> None:
    """P-I1 b : « avancer » ne ramène jamais « Refaire le quiz » avant son jour."""
    light = week(
        2,
        W2,
        [
            t("w2-r", "lire", 60, d(W2, 1)),
            t("w2-p", "pratiquer", 45, d(W2, 2)),
            t("w2-q", "quiz", 20, d(W2, 5)),
        ],
    )
    third = third_week(reads=3, minutes=120)
    third = replace(
        third, modules=[replace(third.modules[0], tasks=[retry(W3), *third.modules[0].tasks])]
    )
    ahead = run(ProgramRows([done_first_week(), light, third]), option="advance")
    dates = {x.task_id: x.planned_date for x in ahead.tasks}
    assert dates["retry"] == W3
    assert any(W2 <= dates[f"w3-r{n}"] < W3 for n in range(3))  # les autres avancent
    assert all(w.after <= w.cap for w in ahead.loads)


def test_push_deadline_moves_overflow_to_suite_weeks() -> None:
    """P-I2 : « Repousser l'échéance » range les semaines à venir sous 60 % du plafond (428) ;
    le surplus part en semaines « Suite », l'échéance recule, sans jamais passer 85 %."""
    plain = run(plan())
    pushed = run(plan(), option="push_deadline")
    assert not plain.deadline_moved
    assert pushed.deadline_moved and pushed.new_weeks
    assert all(w.after <= floor_minutes(714) and w.after <= w.cap for w in pushed.loads)
    by_rank = {w.rank: w.after for w in plain.loads}
    assert all(w.after <= by_rank.get(w.rank, w.after) for w in pushed.loads)
    total = sum(x.minutes for x in plain.tasks)
    pushed_old = sum(x.minutes for x in pushed.tasks if x.suite_rank is None)
    assert pushed_old == total  # rien n'est perdu : les mêmes tâches, plus tard
