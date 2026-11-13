"""Replanification sur les lignes du programme (SPEC F13, D106) : empreinte des lignes et
rangement d'une proposition (`repack`). Fonctions pures, sans base ni modèle.

Seules les tâches à faire bougent, de la semaine en cours et des suivantes ; une tâche garde son
module, seule sa date change (D88 §1 : la semaine d'une tâche est celle de son jour). Le budget
passe avant l'échéance : ce qui ne tient pas part dans des semaines « Suite », quelle que soit
l'option. Le rangement est stable (revue finale de la phase 5, P-I1) : une semaine qui ne reçoit
ni retard ni ajout garde ses dates (`replan_stable.keeps_dates`), et une tâche à faire n'est
jamais placée avant sa date, hors option « avancer », qui n'avance jamais un « Refaire le quiz ».
« Repousser l'échéance » range les semaines à venir sous 60 % du plafond (P-I2) : le surplus part
en semaines « Suite », l'échéance recule. L'écriture est dans `replan_versions`."""

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
    PRACTICE_MINUTES,
    QUIZ_MINUTES,
    PlanningImpossible,
)
from app.features.program.service.replan_rows import (
    NewTask,
    NewWeek,
    PlannedTask,
    Slots,
    WeekBudget,
    open_week,
    week_loads,
)
from app.features.program.service.replan_stable import advance, keeps_dates
from app.features.program.service.rules import UNDERLOAD_SHARE, floor_minutes, is_retry

__all__ = ["NewTask", "NewWeek", "PlannedTask", "RepackResult", "fingerprint", "repack"]

DAYS = 7
PUSH_SHARE = UNDERLOAD_SHARE  # « Repousser l'échéance » : semaines à venir à 60 % du plafond


class ProgramFinished(PlanningImpossible):
    """Plus aucune semaine à replanifier : le programme est terminé."""

    def __init__(self) -> None:
        super().__init__("Le programme est terminé : plus aucune semaine à replanifier.")


def fingerprint(rows: ProgramRows) -> str:
    """sha256 des `(tâche, jour, statut, minutes)` triés : toute modification de January (jour,
    durée, case cochée, ajout, suppression) change l'empreinte."""
    items = sorted(
        (t.task_id, t.planned_date.isoformat(), t.status, t.minutes)
        for week in rows.weeks
        for module in week.modules
        for t in module.tasks
    )
    return hashlib.sha256(json.dumps(items).encode()).hexdigest()


@dataclass(frozen=True)
class RepackResult:
    """`tasks` : toutes les tâches à faire après le rangement (gardées, ajoutées, et pratique et
    quiz des semaines « Suite ») ; `removed` : ids retirés ; `kept` : retraits ignorés (dernier
    quiz ou dernière pratique d'une semaine)."""

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
    module_week: int  # rang (0…) de la semaine du module


def _rows(rows: ProgramRows) -> list[_Row]:
    """Les tâches dans l'ordre du programme (semaine, module, rang), par date ensuite."""
    found = [
        _Row(t, m.module_id, index)
        for index, week in enumerate(rows.weeks)
        for m in week.modules
        for t in m.tasks
    ]
    order = {id(r): n for n, r in enumerate(found)}
    return sorted(found, key=lambda r: (r.task.planned_date, order[id(r)]))


def _start_day(today: date, budget: Budget) -> date:
    """Aujourd'hui, ou lundi prochain s'il ne reste aucun jour de travail cette semaine (le bilan
    du dimanche replanifie à partir de la semaine suivante)."""
    monday = week_start(today)
    left = (today + timedelta(days=n) for n in range((monday + timedelta(days=6) - today).days + 1))
    return today if any(budget.day_capacity(day) > 0 for day in left) else monday + timedelta(DAYS)


def _span(starts: Sequence[date], day: date) -> int:
    """Le rang de la semaine dont les sept jours contiennent `day` (avant la première : 0)."""
    for index, start in enumerate(starts):
        if day < start + timedelta(days=DAYS):
            return index
    return len(starts)


def _drops(found: list[_Row], starts: list[date], drop: Set[str]) -> tuple[set[str], int]:
    """Les retraits faits, et ceux ignorés : jamais le dernier quiz ni la dernière pratique de
    sa semaine (faites comprises)."""
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
        if task.type in ("pratiquer", "quiz") and len(same) == 1:
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
    """Une tâche existante n'est jamais placée avant sa date (`not_before`) ; un « Refaire le
    quiz » ne ferme jamais la semaine à la place de son quiz."""
    draft = TaskDraft.model_construct(
        title=task.title, type=task.type, minutes=task.minutes, done_criterion=task.done_criterion
    )
    floor = task.planned_date if task.task_id else None
    return Entry(draft, (seq, 0, 0), floor, is_retry(task.title, task.type))


@dataclass
class _Queue:
    """Les tâches à ranger, numérotées dans l'ordre de la file (`origin` des entrées)."""

    tasks: list[PlannedTask]

    def entries(self, items: Sequence[PlannedTask]) -> list[Entry]:
        out = []
        for item in items:
            self.tasks.append(item)
            out.append(_entry(item, len(self.tasks) - 1))
        return out


def _own(
    found: list[_Row], starts: list[date], current: int, removed: set[str], add: Sequence[NewTask]
) -> tuple[list[PlannedTask], dict[int, list[PlannedTask]]]:
    """Les retards des semaines passées, puis les tâches à faire de chaque semaine ; un ajout du
    Stratège va à la fin de la semaine de son module si elle est en cours ou à venir, sinon de
    la semaine en cours."""
    late: list[PlannedTask] = []
    own: dict[int, list[PlannedTask]] = {}
    for row in found:
        if row.task.status != "todo" or row.task.task_id in removed:
            continue
        week = _span(starts, row.task.planned_date)
        (late if week < current else own.setdefault(week, [])).append(_planned(row))
    weeks = {r.module_id: r.module_week for r in found}
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


def _budget(
    budget: Budget, cap: int, used: dict[date, int], start: date, from_day: date, *, lower: bool
) -> WeekBudget:
    """Le budget de la semaine, minutes faites retirées. `lower` (« Repousser l'échéance ») :
    plafond abaissé à 60 %, en gardant toujours la place d'une pratique et d'un quiz au-delà des
    minutes faites, et jamais au-delà du plafond (85 %)."""
    week_used = {d: m for d, m in used.items() if start <= d < start + timedelta(days=DAYS)}
    done = sum(week_used.values())
    if lower:
        room = min(cap, done + PRACTICE_MINUTES + QUIZ_MINUTES)
        cap = max(floor_minutes(cap, PUSH_SHARE), room)
    return WeekBudget(
        budget.weekday_minutes, budget.weekend_minutes, max(0, cap - done), week_used, from_day
    )


def _cap(
    budget: Budget, current: bool, override: int | None, option: ReplanOption | None
) -> tuple[int, bool]:
    """Le plafond de la semaine (celui de January pour la semaine en cours, s'il est donné), et
    s'il faut l'abaisser (« Repousser l'échéance », toute autre semaine)."""
    if current and override is not None:
        return override, False
    return budget.cap_minutes, option == "push_deadline"


def _pack(carried: list[Entry], mine: list[Entry], week: WeekBudget, start: date) -> WeekPacking:
    try:
        return pack_week(carried, mine, week, start)
    except NoRoom:
        raise PlanningImpossible() from None


def _kept(queue: _Queue, tasks: list[PlannedTask]) -> list[tuple[int, date]]:
    """Une semaine gardée telle quelle : chaque tâche à sa date."""
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
    """Range la suite du programme (voir le module) ; `PlanningImpossible` si une semaine ne
    tient pas sa pratique et son quiz, ou si le programme est terminé."""
    starts = [week.start_date for week in rows.weeks]
    found = _rows(rows)
    from_day = _start_day(today, budget)
    current = _span(starts, from_day)
    if current >= len(starts):
        raise ProgramFinished()
    removed, kept = _drops(found, starts, drop)
    late, own = _own(found, starts, current, removed, add)
    used = _done_minutes(found)
    queue = _Queue([])
    carried = queue.entries(late)
    placed: list[tuple[int, date]] = []  # (rang dans la file, jour)
    new_weeks: list[NewWeek] = []
    index = current
    while index < len(starts) or carried:
        start = open_week(rows, index, new_weeks, own)
        cap, lower = _cap(budget, index == current, week_cap_override, option)
        week = _budget(budget, cap, used, start, from_day, lower=lower)
        if not carried and keeps_dates(own.get(index, []), week, start):
            placed += _kept(queue, own.get(index, []))  # ni retard ni ajout : dates gardées
            index += 1
            continue
        mine = queue.entries(own.get(index, []))
        packing = _pack(carried, mine, week, start)
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
