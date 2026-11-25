"""Reading a program (SPEC 3.4, D88): rows re-read together (`Loaded`), API view (weeks,
modules, tasks, progress, last difference), rows for a version's snapshot and the current plan
as text for a Strategist revision.

A task's week is that of its planned day (seven days from the start of the week): the load and
rules of a week are read from the calendar."""

import builtins
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.program import Module, PlanVersion, Program, Task, Week
from app.features.lessons.service.status import read_with_open_sessions, shown
from app.features.program.repository import (
    ModuleExtrasRepository,
    ModuleRepository,
    PlanVersionRepository,
    ProgramRepository,
    TaskRepository,
    WeekRepository,
    validated_programs,
)
from app.features.program.schemas import (
    ModuleOut,
    MovedTaskOut,
    PlanDiffOut,
    ProgramOut,
    ProgramSummaryOut,
    ProgressOut,
    TaskOut,
    WeekOut,
)
from app.features.program.service.diff import ModuleRow, ProgramRows, TaskRow, WeekRow
from app.features.settings.service import scheduled_users

DAYS_PER_WEEK = 7


def program_not_found() -> AppError:
    return AppError("program_not_found", "Program not found.", 404)


@dataclass
class Loaded:
    program: Program
    weeks: list[Week]  # by rank
    modules: list[Module]  # by week then rank
    tasks: list[Task]  # by module then rank

    def week_of(self, day: date) -> Week | None:
        """The week whose seven days contain `day`, `None` outside the program."""
        for week in self.weeks:
            if week.start_date <= day < week.start_date + timedelta(days=DAYS_PER_WEEK):
                return week
        return None

    def tasks_of_module(self, module_id: str) -> list[Task]:
        return [task for task in self.tasks if task.module_id == module_id]

    def week_load(self, week: Week) -> int:
        return sum(t.minutes for t in self.tasks if self.week_of(t.planned_date) is week)


async def load(db: AsyncSession, user_id: str, program_id: str) -> Loaded:
    """The user's program and its rows, re-read; 404 if it is not theirs."""
    program = await ProgramRepository(db, user_id).get_fresh(program_id)
    if program is None:
        raise program_not_found()
    weeks = await WeekRepository(db, user_id).for_program(program_id)
    rank = {week.id: week.rank for week in weeks}
    modules = await ModuleRepository(db, user_id).for_program(program_id)
    modules.sort(key=lambda m: (rank.get(m.week_id, 0), m.rank))
    order = {module.id: index for index, module in enumerate(modules)}
    tasks = await TaskRepository(db, user_id).for_program(program_id)
    tasks.sort(key=lambda t: (order.get(t.module_id, 0), t.rank))
    return Loaded(program, weeks, modules, tasks)


def _task_row(t: Task) -> TaskRow:
    return TaskRow(
        t.title,
        t.type,  # type: ignore[arg-type]  # colonne texte, valeurs de TaskType
        t.minutes,
        t.planned_date,
        t.already_known,
        task_id=t.id,
        status=t.status,
        done_criterion=t.done_criterion,
    )


def rows_of(loaded: Loaded) -> ProgramRows:
    """The program as rows, for a version's snapshot (`diff.snapshot`)."""
    weeks = [
        WeekRow(
            rank=week.rank,
            theme=week.theme,
            start_date=week.start_date,
            modules=[
                ModuleRow(
                    title=module.title,
                    skipped=module.skipped,
                    tasks=[_task_row(t) for t in loaded.tasks_of_module(module.id)],
                    module_id=module.id,
                )
                for module in loaded.modules
                if module.week_id == week.id
            ],
            objective=week.objective,
            deliverable=week.deliverable,
        )
        for week in loaded.weeks
    ]
    return ProgramRows(weeks)


def plan_text(loaded: Loaded) -> str:
    """The current plan as text (January's edits included), for a revision."""
    lines: list[str] = []
    for week in loaded.weeks:
        lines.append(f"Week {week.rank} (from {week.start_date:%d/%m}): {week.theme}")
        for module in (m for m in loaded.modules if m.week_id == week.id):
            if module.skipped:
                lines.append(f'  Module "{module.title}": already known, skipped')
                continue
            lines.append(f'  Module "{module.title}"')
            lines += [
                f"  - {t.planned_date:%d/%m} : {t.title} ({t.type}, {t.minutes} min"
                + (", faite)" if t.status == "done" else ")")
                for t in loaded.tasks_of_module(module.id)
            ]
    return "\n".join(lines)


def task_out(task: Task) -> TaskOut:
    return TaskOut.model_validate(task, from_attributes=True)


def progress_of(tasks: builtins.list[Task]) -> ProgressOut:
    done = [t for t in tasks if t.status == "done"]
    return ProgressOut(
        done_tasks=len(done),
        total_tasks=len(tasks),
        done_minutes=sum(t.minutes for t in done),
        total_minutes=sum(t.minutes for t in tasks),
    )


def _diff_out(version: PlanVersion | None) -> PlanDiffOut | None:
    """The difference of the last version, `None` for the first (everything is added in it)."""
    if version is None or version.version <= 1 or not version.diff:
        return None
    diff: dict[str, Any] = version.diff
    moved = [MovedTaskOut(task=m[0], before=m[1], after=m[2]) for m in diff.get("moved", [])]
    return PlanDiffOut(
        added=list(diff.get("added", [])),
        removed=list(diff.get("removed", [])),
        moved=moved,
        weeks_before=int(diff.get("weeks_before", 0)),
        weeks_after=int(diff.get("weeks_after", 0)),
    )


def day_budget(version: PlanVersion | None) -> tuple[int, int]:
    """`(Monday to Friday, Saturday)` of the version's budget (minutes per day)."""
    budget = (version.snapshot if version is not None else {}).get("budget", {})
    return int(budget.get("weekday_minutes", 0)), int(budget.get("weekend_minutes", 0))


async def _modules_out(db: AsyncSession, user_id: str, loaded: Loaded) -> dict[str, ModuleOut]:
    extras = ModuleExtrasRepository(db, user_id)
    rows, open_ids = await read_with_open_sessions(
        db,
        user_id,
        loaded.program.id,
        lambda: extras.lessons(loaded.program.id),
        lambda found: [(row[1], row[2]) for row in found.values()],
    )
    counts = await extras.resource_counts(loaded.program.id)
    # Lesson interrupted outside the port: shown as failed, without a write (D91, order D97).
    lessons = {key: (row[0], shown(row[1], row[2], None, open_ids)[0]) for key, row in rows.items()}
    return {
        module.id: ModuleOut(
            id=module.id,
            rank=module.rank,
            title=module.title,
            skills=[str(s) for s in module.skills],
            prerequisites=[str(p) for p in module.prerequisites],
            skipped=module.skipped,
            lesson_id=lessons[module.id][0] if module.id in lessons else None,
            lesson_status=lessons[module.id][1] if module.id in lessons else None,  # type: ignore[arg-type]
            resources_count=counts.get(module.id, 0),
            official_urls=[str(u) for u in module.official_urls],
            legacy=[str(n) for n in module.legacy],
            tasks=[task_out(t) for t in loaded.tasks_of_module(module.id)],
        )
        for module in loaded.modules
    }


def _week_out(loaded: Loaded, week: Week, modules: dict[str, ModuleOut]) -> WeekOut:
    load_minutes = loaded.week_load(week)
    return WeekOut(
        id=week.id,
        rank=week.rank,
        theme=week.theme,
        objective=week.objective,
        deliverable=week.deliverable,
        start_date=week.start_date,
        stage=week.stage,  # type: ignore[arg-type]  # colonne texte, valeurs de Stage
        rationale=week.rationale,
        load_minutes=load_minutes,
        load_hours=round(load_minutes / 30) / 2,
        modules=[modules[m.id] for m in loaded.modules if m.week_id == week.id],
    )


async def view_of(db: AsyncSession, user_id: str, loaded: Loaded) -> ProgramOut:
    program = loaded.program
    latest = await PlanVersionRepository(db, user_id).latest(program.id)
    weekday, weekend = day_budget(latest)
    modules = await _modules_out(db, user_id, loaded)
    return ProgramOut(
        id=program.id,
        goal_id=program.goal_id,
        title=program.title,
        status=program.status,  # type: ignore[arg-type]  # colonne texte, valeurs de ProgramStatus
        version=program.version,
        start_date=program.start_date,
        weekly_minutes=program.weekly_minutes,
        cap_minutes=program.cap_minutes,
        weekday_minutes=weekday,
        weekend_minutes=weekend,
        session_id=program.session_id,
        weeks=[_week_out(loaded, week, modules) for week in loaded.weeks],
        progress=progress_of(loaded.tasks),
        diff=_diff_out(latest),
    )


async def get_program(db: AsyncSession, user_id: str, program_id: str) -> ProgramOut:
    return await view_of(db, user_id, await load(db, user_id, program_id))


async def list_programs(db: AsyncSession, user_id: str) -> builtins.list[ProgramSummaryOut]:
    programs = await ProgramRepository(db, user_id).list_recent()
    weeks = await WeekRepository(db, user_id).count_by_program()
    tasks = TaskRepository(db, user_id)
    return [
        ProgramSummaryOut(
            id=p.id,
            goal_id=p.goal_id,
            title=p.title,
            status=p.status,  # type: ignore[arg-type]
            start_date=p.start_date,
            weeks=weeks.get(p.id, 0),
            progress=progress_of(await tasks.for_program(p.id)),
        )
        for p in programs
    ]


def module_not_found() -> AppError:
    return AppError("module_not_found", "Module not found.", 404)


async def program_of_module(db: AsyncSession, user_id: str, module_id: str) -> str:
    """The program of one of the user's modules; 404 `module_not_found` if it is not theirs."""
    module = await ModuleRepository(db, user_id).get(module_id)
    if module is None:
        raise module_not_found()
    return module.program_id


async def list_validated_programs(db: AsyncSession) -> builtins.list[tuple[str, str]]:
    """`(user, program)` of the validated programs of the accounts whose first launch is
    finished (the rule of `GET /settings`, D183, D197): a read without `user_id` reserved for
    scheduled tasks (lessons, statements, weekly review; D91), ids only."""
    onboarded = set(await scheduled_users(db))
    return [pair for pair in await validated_programs(db) if pair[0] in onboarded]
