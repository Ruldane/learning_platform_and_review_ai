"""Recherche déterministe d’une semaine faisable sans altérer l’ordre pédagogique."""

from dataclasses import dataclass, field
from datetime import date, datetime

from app.db.models.program import Task
from app.features.interprogram_planning.capacity import fixed_days
from app.features.interprogram_planning.prerequisites import ModuleWork, Prerequisites, module_work
from app.features.interprogram_planning.schemas import (
    Issue,
    SharedPlacement,
    SharedPrerequisite,
    SharedTaskRef,
    SharedWeekDay,
    SharedWeekOption,
    SharedWeekSnapshot,
)
from app.features.interprogram_planning.sources import WeekFacts


def _task_ref(group: ModuleWork, task: Task) -> SharedTaskRef:
    return SharedTaskRef(
        task_id=task.id,
        program_id=task.program_id,
        module_id=task.module_id,
        module_title=group.module.title,
        title=task.title,
        from_date=task.planned_date,
        minutes=task.minutes,
    )


@dataclass
class Packing:
    days: list[SharedWeekDay]
    placements: list[SharedPlacement] = field(default_factory=list)
    unresolved: list[SharedTaskRef] = field(default_factory=list)
    requirements: dict[str, list[SharedPrerequisite]] = field(default_factory=dict)
    issues: list[Issue] = field(default_factory=list)
    scheduled_modules: dict[str, date] = field(default_factory=dict)

    def issue(self, issue: Issue) -> None:
        if issue not in self.issues:
            self.issues.append(issue)


def _pack_module(
    packing: Packing, group: ModuleWork, tasks: list[Task], earliest: date
) -> list[SharedPlacement]:
    # Une recherche infructueuse ne réserve aucune minute pour un demi-module.
    reservations = [day.planned_minutes for day in packing.days]
    placements = []
    for task in tasks:
        original_week = group.program.week_of(task.planned_date)
        for index, day in enumerate(packing.days):
            remaining = day.capacity_minutes - day.reserved_minutes - reservations[index]
            if day.date < earliest or remaining < task.minutes:
                continue
            if group.program.week_of(day.date) is not original_week:
                continue
            reservations[index] += task.minutes
            earliest = day.date
            placements.append(
                SharedPlacement(**_task_ref(group, task).model_dump(), planned_date=day.date)
            )
            break
        else:
            return []
    for day, minutes in zip(packing.days, reservations, strict=True):
        day.planned_minutes = minutes
    return placements


def _record_module(packing: Packing, group: ModuleWork, tasks: list[Task], earliest: date) -> None:
    placements = _pack_module(packing, group, tasks, earliest)
    if not placements:
        packing.issue("capacity")
        packing.unresolved.extend(_task_ref(group, task) for task in tasks)
        return
    packing.placements.extend(placements)
    dates = {entry.task_id: entry.planned_date for entry in placements}
    incomplete = [source for source in group.tasks if source.status != "done"]
    if all(source.id in dates for source in incomplete):
        packing.scheduled_modules[group.module.id] = max(dates.values())


def _place(
    packing: Packing,
    candidates: list[tuple[ModuleWork, list[Task]]],
    rules: Prerequisites,
    week_start: date,
) -> None:
    pending = candidates
    while pending:
        waiting = []
        for group, tasks in pending:
            requirements, start = rules.read(group, packing.scheduled_modules, week_start)
            packing.requirements[group.module.id] = requirements
            if start is None:
                waiting.append((group, tasks))
                continue
            _record_module(packing, group, tasks, start)
        if len(waiting) == len(pending):
            packing.issue("prerequisites")
            packing.unresolved.extend(
                _task_ref(group, task) for group, tasks in waiting for task in tasks
            )
            break
        pending = waiting


def _candidates(
    facts: WeekFacts,
    groups: list[ModuleWork],
) -> list[tuple[ModuleWork, list[Task]]]:
    booked = {item.task_id for item in facts.bookings}
    movable = {
        task.id for task in facts.scheduled if task.status == "todo" and task.id not in booked
    }
    groups_tasks = [
        (
            group,
            [
                task
                for task in group.tasks
                if task.id in movable and group.program.week_of(task.planned_date) is not None
            ],
        )
        for group in groups
        if not group.module.skipped
    ]
    return [(group, tasks) for group, tasks in groups_tasks if tasks]


def prepare(facts: WeekFacts, now: datetime) -> SharedWeekSnapshot:
    groups = module_work(facts)
    candidates = _candidates(facts, groups)
    moving = {task.id for _, tasks in candidates for task in tasks}
    fixed = [task for task in facts.scheduled if task.id not in moving]
    packing = Packing(fixed_days(facts, fixed, now))
    planned = sum(task.minutes for task in facts.scheduled)
    if not candidates:
        packing.issue("no_tasks")
    if planned > facts.budget.cap_minutes:
        packing.issue("weekly_budget")
    for group, tasks in candidates:
        for week in {group.program.week_of(task.planned_date) for task in tasks}:
            if (
                week is not None
                and group.program.week_load(week) > group.program.program.cap_minutes
            ):
                packing.issue("program_budget")
    _place(packing, candidates, Prerequisites(groups), facts.week_start)
    return SharedWeekSnapshot(
        week_start=facts.week_start,
        programs=[
            SharedWeekOption(id=item.program.id, title=item.program.title)
            for item in facts.programs
        ],
        cap_minutes=facts.budget.cap_minutes,
        planned_minutes=planned,
        days=packing.days,
        placements=packing.placements,
        prerequisites=[row for group in packing.requirements.values() for row in group],
        unplaced=packing.unresolved,
        issues=packing.issues,
    )
