"""Pièces du rangement d'une replanification (`replanning.repack`, D106) : tâches rangées,
semaines « Suite », budget d'une semaine entamée, charges et règles des semaines touchées, et le
plan après la proposition (pour l'instantané et la différence). L'avance (« avancer ») et les
semaines gardées telles quelles sont dans `replan_stable`. Fonctions pures."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from typing import Any, Protocol

from app.agents.tools.replan_port import WeekLoad
from app.db.models.program import TaskType
from app.features.program.service.budget import Budget
from app.features.program.service.diff import ModuleRow, ProgramRows, TaskRow, WeekRow
from app.features.program.service.planning import (
    MAX_WEEKS,
    PRACTICE_MINUTES,
    QUIZ_MINUTES,
    PlanningImpossible,
)
from app.features.program.service.rules import week_breaks

DAYS = 7
SUITE = "Suite : "
PRACTICE_CRITERION = "Produire un résultat que l'on peut montrer et expliquer"
QUIZ_CRITERION = "Répondre à toutes les questions puis relire les erreurs"


@dataclass(frozen=True)
class NewTask:
    """Une tâche ajoutée par le Stratège (« approfondir ») dans un module existant."""

    module_id: str
    title: str
    type: TaskType
    minutes: int
    done_criterion: str


@dataclass(frozen=True)
class PlannedTask:
    """Une tâche à faire après le rangement. `task_id` vide : tâche neuve, dans `module_id`
    (ajout du Stratège) ou dans le module de la semaine « Suite » de rang `suite_rank`."""

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
    """Une semaine « Suite » : ce qui ne tient pas dans le budget, plutôt qu'un dépassement."""

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
    """Le budget d'une semaine entamée : plafond (85 %, ou celui de January cette semaine) moins
    les minutes déjà faites, jours passés fermés, minutes faites retirées de leur jour."""

    cap: int = 0
    used: Mapping[date, int] = field(default_factory=dict)
    from_day: date = date.min

    @property
    def cap_minutes(self) -> int:
        return self.cap

    def day_capacity(self, day: date) -> int:
        if day < self.from_day:
            return 0
        return max(0, super().day_capacity(day) - self.used.get(day, 0))


def suite_week(last: WeekRow, rank: int, last_start: date, count: int) -> NewWeek:
    """La semaine « Suite » de rang `rank`, après la dernière (`count` semaines) ; thème, objectif
    et livrable repris de la dernière semaine."""
    theme = last.theme.removeprefix(SUITE)
    return NewWeek(
        rank,
        f"{SUITE}{theme}"[:200],
        f"{last.objective.removesuffix(' (suite)')} (suite)"[:300],
        f"{last.deliverable.removesuffix(' (suite)')} (suite)"[:300],
        last_start + timedelta(days=DAYS * (rank - count)),
    )


def suite_tasks(week: NewWeek) -> list[PlannedTask]:
    """La pratique et le quiz d'une semaine « Suite » (chaque semaine garde les siens)."""
    theme = week.theme.removeprefix(SUITE)
    day = week.start_date
    return [
        PlannedTask(
            "",
            day,
            f"Pratiquer : {theme}"[:120],
            "pratiquer",
            PRACTICE_MINUTES,
            PRACTICE_CRITERION,
            "",
            week.rank,
        ),
        PlannedTask(
            "",
            day,
            f"Faire le quiz de la semaine {week.rank}",
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
    """Le début de la semaine `index` ; au-delà de la dernière, une semaine « Suite » est ouverte
    avec sa pratique et son quiz (52 semaines au plus)."""
    starts = [week.start_date for week in rows.weeks]
    if index >= MAX_WEEKS:
        raise PlanningImpossible("Le programme dépasse 52 semaines avec ce budget.")
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
    """Les semaines du rangement : débuts (anciennes puis « Suite »), rang de la semaine en
    cours, toutes les tâches d'origine, budget et premier jour ouvert."""

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
    """Charge avant et après de chaque semaine touchée, et ses règles (85 % ou le plafond de
    January, une pratique, un quiz) : une règle cassée lève `PlanningImpossible`."""
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
    """Le programme tel que la proposition le laisserait (instantané et différence)."""
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
