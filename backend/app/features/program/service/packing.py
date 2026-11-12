"""Placement des tâches d'une semaine sur ses jours, sans jamais dépasser 85 % du budget.

Une semaine se range en deux temps : la pratique et le quiz de la semaine sont réservés d'abord
(leur minutes sont retirées du plafond et de leur jour), puis les autres tâches suivent dans
leur ordre, sans en doubler aucune ; ce qui ne tient plus est reporté à la semaine suivante.
Une semaine rangée trop légère avance ensuite des tâches de la suivante (`pull_forward`, D98).
Aucune donnée n'est écrite ici : des fonctions pures, testées sans base.
"""

from dataclasses import dataclass, replace
from datetime import date, timedelta

from app.agents.tools.plan_schema import ModuleDraft, TaskDraft
from app.db.models.program import TaskType
from app.features.program.service.advance import Dated, WeekSlots, plan_advances
from app.features.program.service.budget import Budget

DAYS_PER_WEEK = 7


class NoRoom(Exception):
    """La semaine ne peut pas contenir ses tâches réservées (pratique, quiz)."""


@dataclass(frozen=True)
class Entry:
    """Une tâche à placer ; `origin` = (semaine, module, tâche) du brouillon, ordre naturel."""

    task: TaskDraft
    origin: tuple[int, int, int]


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
    """Le dernier quiz de la semaine : il ferme la semaine."""
    quizzes = [entry for entry in own if entry.task.type == "quiz"]
    return quizzes[-1] if quizzes else None


def first_practice(own: list[Entry]) -> Entry | None:
    """La première pratique de la semaine : sa place est réservée d'avance."""
    practices = [entry for entry in own if entry.task.type == "pratiquer"]
    return practices[0] if practices else None


def _quiz_day(days: list[date], remaining: dict[date, int], minutes: int) -> date:
    """Le dernier jour qui a la place du quiz (samedi d'abord)."""
    for day in reversed(days):
        if remaining[day] >= minutes:
            return day
    raise NoRoom


def pack_week(carried: list[Entry], own: list[Entry], budget: Budget, start: date) -> WeekPacking:
    """Place `carried` (reportées) puis `own` (propres à la semaine) sur sept jours depuis `start`.

    L'ordre est conservé : dès qu'une tâche ne tient plus, toutes les suivantes sont reportées
    (un chapitre ne passe pas avant celui qui le précède). Le quiz est la dernière tâche de la
    semaine : les autres tâches ne dépassent pas son jour.
    """
    days = week_days(start)
    remaining = {day: budget.day_capacity(day) for day in days}
    quiz, practice = final_quiz(own), first_practice(own)
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
        day = next((d for d in usable if remaining[d] >= practice.task.minutes), None)
        if day is None:
            raise NoRoom
        remaining[day] -= practice.task.minutes
        placed.append(Placement(practice, day))
    queue = carried + [entry for entry in own if entry not in reserved]
    deferred: list[Entry] = []
    charge, cursor = 0, 0
    for entry in queue:
        minutes = entry.task.minutes
        index = next(
            (i for i in range(cursor, len(usable)) if remaining[usable[i]] >= minutes), None
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


@dataclass(frozen=True)
class ScheduledPlan:
    weeks: list[ScheduledWeek]
    skipped_modules: list[str]
    moved_tasks: int


SUITE = " (suite)"


def _reserved(tasks: list[ScheduledTask]) -> set[int]:
    """Rangs du quiz qui ferme la semaine (le dernier) et de sa première pratique."""
    quizzes = [i for i, task in enumerate(tasks) if task.type == "quiz"]
    practices = [i for i, task in enumerate(tasks) if task.type == "pratiquer"]
    return set(quizzes[-1:] + practices[:1])


def _slots(week: ScheduledWeek) -> WeekSlots:
    reserved = _reserved(week.tasks)
    return WeekSlots(
        week.start_date,
        [Dated(t.minutes, t.planned_date, i in reserved) for i, t in enumerate(week.tasks)],
    )


def _module_slot(modules: list[ModuleDraft], source: ModuleDraft) -> int:
    """Rang, dans `modules`, du module d'origine d'une tâche avancée : le même module (titre sans
    « (suite) », mêmes compétences) s'il y est, sinon ajouté sous son titre suivi de « (suite) »."""
    base = source.title.removesuffix(SUITE)
    for index, module in enumerate(modules):
        if module.title.removesuffix(SUITE) == base and module.skills == source.skills:
            return index
    modules.append(source.model_copy(update={"title": f"{base[:112]}{SUITE}"}))
    return len(modules) - 1


def _draft(task: ScheduledTask) -> TaskDraft:
    return TaskDraft.model_construct(
        title=task.title, type=task.type, minutes=task.minutes, done_criterion=task.done_criterion
    )


def _rebuilt(
    week: ScheduledWeek, modules: list[ModuleDraft], tasks: list[ScheduledTask]
) -> ScheduledWeek:
    """La semaine avec ces tâches : modules vidés retirés, rangs de module recalculés."""
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
    """Les tâches `days` (rang dans `source` → jour) passent dans `receiver`, avant son quiz."""
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
    """Chaque semaine (sauf la dernière) sous `floor_share` × plafond avance, dans l'ordre, des
    tâches de la suivante (jamais son quiz ni sa pratique réservée) sur ses jours qui ont la
    place, sans dépasser le plafond (`advance.plan_advances`). Une tâche avancée garde son module,
    ajouté à la semaine qui la reçoit. Rend de nouvelles semaines ; `weeks` est inchangé."""
    moves = plan_advances([_slots(week) for week in weeks], budget, floor_share=floor_share)
    by_source: dict[int, dict[int, date]] = {}
    for move in moves:
        by_source.setdefault(move.source, {})[move.index] = move.day
    result = list(weeks)
    for source, days in sorted(by_source.items()):
        result[source - 1], result[source] = _move(result[source - 1], result[source], days)
    return result
