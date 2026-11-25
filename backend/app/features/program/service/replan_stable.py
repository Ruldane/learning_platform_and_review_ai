"""Stable packing of a replanning (D106, final review of phase 5, P-I1): what must not move does
not move. A week that receives neither delay nor addition keeps the dates of its tasks (chosen
by January included) as long as they fit under its cap and none is past; "advance" never brings
a "Retake the quiz" back before its day (F9: day +2). Pure functions."""

from collections.abc import Sequence
from datetime import date, timedelta

from app.features.program.service.advance import Dated, WeekSlots, plan_advances
from app.features.program.service.replan_rows import PlannedTask, Slots, WeekBudget
from app.features.program.service.rules import is_retry

DAYS = 7


def keeps_dates(tasks: Sequence[PlannedTask], week: WeekBudget, start: date) -> bool:
    """True if the week can keep the dates of its tasks to do as they are: no new task, all dated
    within its days still open, under its cap (minutes already done removed). On days covered by the
    calendar, the tasks to do must also fit in the observed contiguous slot. Elsewhere, the manual
    choice of a busy day stays valid."""
    first, end = max(start, week.from_day), start + timedelta(days=DAYS)
    agenda: dict[date, int] = {}
    for task in tasks:
        if task.planned_date in week.daily_caps:
            agenda[task.planned_date] = agenda.get(task.planned_date, 0) + task.minutes
    return (
        all(minutes <= week.daily_caps[day] for day, minutes in agenda.items())
        and all(task.task_id for task in tasks)
        and all(first <= task.planned_date < end for task in tasks)
        and sum(task.minutes for task in tasks) <= week.cap_minutes
    )


def _reserved(items: list[PlannedTask]) -> set[int]:
    """Ranks of the last quiz, of the first practice and of a week's "Retake the quiz" tasks (never
    advanced)."""
    quizzes = [i for i, t in enumerate(items) if t.type == "quiz"]
    practices = [i for i, t in enumerate(items) if t.type == "practice"]
    retries = [i for i, t in enumerate(items) if is_retry(t.title, t.type)]
    return set(quizzes[-1:] + practices[:1] + retries)


def advance(tasks: list[PlannedTask], slots: Slots, *, skip_current: bool) -> list[PlannedTask]:
    """Advancing (D98, `plan_advances` at 100% of the cap) from the current week (the next one
    if January has given their hours for the week): only the date of the tasks changes."""
    first = slots.current + (1 if skip_current else 0)
    weeks: list[WeekSlots] = []
    owners: list[list[int | None]] = []  # rank in `tasks` of each dated task (done: None)
    for index in range(first, len(slots.starts)):
        mine = sorted(
            (n for n, t in enumerate(tasks) if slots.within(index, t.planned_date)),
            key=lambda n: tasks[n].planned_date,
        )
        reserved = _reserved([tasks[n] for n in mine])
        done = slots.done(index)
        dated = [Dated(t.minutes, t.planned_date, True) for t in done]
        dated += [
            Dated(tasks[n].minutes, tasks[n].planned_date, i in reserved)
            for i, n in enumerate(mine)
        ]
        weeks.append(WeekSlots(slots.starts[index], dated))
        owners.append([None] * len(done) + list(mine))
    budget = WeekBudget(
        slots.budget.weekday_minutes,
        slots.budget.weekend_minutes,
        slots.budget.cap_minutes,
        {},
        slots.from_day,
        daily_caps=slots.budget.daily_caps,
    )
    result = list(tasks)
    for move in plan_advances(weeks, budget, floor_share=1.0):
        owner = owners[move.source][move.index]
        if owner is not None:
            result[owner] = result[owner].moved(move.day)
    return result
