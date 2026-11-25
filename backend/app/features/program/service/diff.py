"""Snapshot of a plan and difference between two versions (`plan_versions`, SPEC 3.4)."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.db.models.program import TaskType
from app.features.program.service.planning import ScheduledPlan


@dataclass(frozen=True)
class TaskRow:
    """A task; `task_id`, `status` and `done_criterion` do not go into the snapshot: they serve
    replanning (fingerprint, frozen tasks, D106)."""

    title: str
    type: TaskType
    minutes: int
    planned_date: date
    already_known: bool = False
    task_id: str = ""
    status: str = "todo"
    done_criterion: str = ""


@dataclass(frozen=True)
class ModuleRow:
    title: str
    skipped: bool = False
    tasks: list[TaskRow] = field(default_factory=list)
    module_id: str = ""


@dataclass(frozen=True)
class WeekRow:
    rank: int
    theme: str
    start_date: date
    modules: list[ModuleRow] = field(default_factory=list)
    objective: str = ""
    deliverable: str = ""


@dataclass(frozen=True)
class ProgramRows:
    """The program as the database rows describe it (weeks, modules, tasks)."""

    weeks: list[WeekRow]


@dataclass(frozen=True)
class PlanDiff:
    added: list[str]
    removed: list[str]
    moved: list[tuple[str, str, str]]  # (task, date before, date after)
    weeks_before: int
    weeks_after: int

    def to_json(self) -> dict[str, Any]:
        """Form stored in `plan_versions.diff`."""
        return {
            "added": self.added,
            "removed": self.removed,
            "moved": [list(move) for move in self.moved],
            "weeks_before": self.weeks_before,
            "weeks_after": self.weeks_after,
        }


def _task_json(title: str, kind: str, minutes: int, day: date, known: bool) -> dict[str, Any]:
    return {
        "title": title,
        "type": kind,
        "minutes": minutes,
        "planned_date": day.isoformat(),
        "already_known": known,
    }


def _from_plan(plan: ScheduledPlan) -> dict[str, Any]:
    weeks = []
    for week in plan.weeks:
        modules = [
            {
                "title": module.title,
                "tasks": [
                    _task_json(t.title, t.type, t.minutes, t.planned_date, t.already_known)
                    for t in week.tasks
                    if t.module_index == index
                ],
            }
            for index, module in enumerate(week.modules)
        ]
        weeks.append(
            {
                "rank": week.rank,
                "theme": week.theme,
                "start_date": week.start_date.isoformat(),
                "modules": modules,
            }
        )
    return {"weeks": weeks, "skipped": list(plan.skipped_modules)}


def _from_rows(rows: ProgramRows) -> dict[str, Any]:
    weeks = [
        {
            "rank": week.rank,
            "theme": week.theme,
            "start_date": week.start_date.isoformat(),
            "modules": [
                {
                    "title": module.title,
                    "tasks": [
                        _task_json(t.title, t.type, t.minutes, t.planned_date, t.already_known)
                        for t in module.tasks
                    ],
                }
                for module in week.modules
                if not module.skipped
            ],
        }
        for week in rows.weeks
    ]
    skipped = [m.title for week in rows.weeks for m in week.modules if m.skipped]
    return {"weeks": weeks, "skipped": skipped}


def snapshot(plan: ScheduledPlan | ProgramRows) -> dict[str, Any]:
    """JSON form of `plan_versions.snapshot` (dates in ISO), the same for both sources."""
    return _from_plan(plan) if isinstance(plan, ScheduledPlan) else _from_rows(plan)


def _task_dates(snap: Mapping[str, Any]) -> dict[str, str]:
    """Maps "{module} / {task}" to the planned date; a duplicate gets its order number."""
    dates: dict[str, str] = {}
    for week in snap.get("weeks", []):
        for module in week["modules"]:
            for task in module["tasks"]:
                key = f"{module['title']} / {task['title']}"
                suffix = 2
                while key in dates:
                    key = f"{module['title']} / {task['title']} ({suffix})"
                    suffix += 1
                dates[key] = task["planned_date"]
    return dates


def diff_plans(before: Mapping[str, Any] | None, after: Mapping[str, Any]) -> PlanDiff:
    """Tasks added, removed and moved; `before` absent: everything is added."""
    old = _task_dates(before) if before is not None else {}
    new = _task_dates(after)
    return PlanDiff(
        added=[key for key in new if key not in old],
        removed=[key for key in old if key not in new],
        moved=[(key, old[key], day) for key, day in new.items() if key in old and old[key] != day],
        weeks_before=len(before.get("weeks", [])) if before is not None else 0,
        weeks_after=len(after.get("weeks", [])),
    )
