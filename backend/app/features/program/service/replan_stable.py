"""Rangement stable d'une replanification (D106, revue finale de la phase 5, P-I1) : ce qui ne
doit pas bouger ne bouge pas. Une semaine qui ne reçoit ni retard ni ajout garde les dates de ses
tâches (choisies par January comprises) tant qu'elles tiennent sous son plafond et qu'aucune
n'est passée ; « avancer » ne ramène jamais un « Refaire le quiz » avant son jour (F9 : J+2).
Fonctions pures."""

from collections.abc import Sequence
from datetime import date, timedelta

from app.features.program.service.advance import Dated, WeekSlots, plan_advances
from app.features.program.service.replan_rows import PlannedTask, Slots, WeekBudget
from app.features.program.service.rules import is_retry

DAYS = 7


def keeps_dates(tasks: Sequence[PlannedTask], week: WeekBudget, start: date) -> bool:
    """Vrai si la semaine peut garder les dates de ses tâches à faire telles quelles : aucune
    tâche neuve, toutes datées dans ses jours encore ouverts, sous son plafond (minutes faites
    déjà retirées). La capacité du jour n'est pas revérifiée : January peut charger un jour à
    son gré tant que la semaine tient (`editing.check_weeks`)."""
    first, end = max(start, week.from_day), start + timedelta(days=DAYS)
    return (
        all(task.task_id for task in tasks)
        and all(first <= task.planned_date < end for task in tasks)
        and sum(task.minutes for task in tasks) <= week.cap_minutes
    )


def _reserved(items: list[PlannedTask]) -> set[int]:
    """Rangs du dernier quiz, de la première pratique et des « Refaire le quiz » d'une semaine
    (jamais avancés)."""
    quizzes = [i for i, t in enumerate(items) if t.type == "quiz"]
    practices = [i for i, t in enumerate(items) if t.type == "pratiquer"]
    retries = [i for i, t in enumerate(items) if is_retry(t.title, t.type)]
    return set(quizzes[-1:] + practices[:1] + retries)


def advance(tasks: list[PlannedTask], slots: Slots, *, skip_current: bool) -> list[PlannedTask]:
    """« Avancer » (D98, `plan_advances` à 100 % du plafond) depuis la semaine en cours (la
    suivante si January a donné ses heures de la semaine) : seule la date des tâches change."""
    first = slots.current + (1 if skip_current else 0)
    weeks: list[WeekSlots] = []
    owners: list[list[int | None]] = []  # rang dans `tasks` de chaque tâche datée (faites : None)
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
    )
    result = list(tasks)
    for move in plan_advances(weeks, budget, floor_share=1.0):
        owner = owners[move.source][move.index]
        if owner is not None:
            result[owner] = result[owner].moved(move.day)
    return result
