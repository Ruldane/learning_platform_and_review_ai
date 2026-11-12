"""Lecture d'un programme (SPEC 3.4, D88) : lignes relues ensemble (`Loaded`), vue de l'API
(semaines, modules, tâches, avancement, dernière différence), lignes pour l'instantané d'une
version et plan courant en texte pour une révision du Stratège.

La semaine d'une tâche est celle de son jour planifié (sept jours depuis le début de la
semaine) : la charge et les règles d'une semaine se lisent sur le calendrier."""

import builtins
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.program import Module, PlanVersion, Program, Task, Week
from app.features.lessons.service.status import open_lesson_sessions, shown
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

DAYS_PER_WEEK = 7


def program_not_found() -> AppError:
    return AppError("program_not_found", "Programme introuvable.", 404)


@dataclass
class Loaded:
    program: Program
    weeks: list[Week]  # par rang
    modules: list[Module]  # par semaine puis rang
    tasks: list[Task]  # par module puis rang

    def week_of(self, day: date) -> Week | None:
        """La semaine dont les sept jours contiennent `day`, `None` hors du programme."""
        for week in self.weeks:
            if week.start_date <= day < week.start_date + timedelta(days=DAYS_PER_WEEK):
                return week
        return None

    def tasks_of_module(self, module_id: str) -> list[Task]:
        return [task for task in self.tasks if task.module_id == module_id]

    def week_load(self, week: Week) -> int:
        return sum(t.minutes for t in self.tasks if self.week_of(t.planned_date) is week)


async def load(db: AsyncSession, user_id: str, program_id: str) -> Loaded:
    """Programme de l'utilisateur et ses lignes, relus ; 404 s'il n'est pas à lui."""
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


def rows_of(loaded: Loaded) -> ProgramRows:
    """Le programme en lignes, pour l'instantané d'une version (`diff.snapshot`)."""
    weeks = [
        WeekRow(
            rank=week.rank,
            theme=week.theme,
            start_date=week.start_date,
            modules=[
                ModuleRow(
                    title=module.title,
                    skipped=module.skipped,
                    tasks=[
                        TaskRow(t.title, t.type, t.minutes, t.planned_date, t.already_known)  # type: ignore[arg-type]
                        for t in loaded.tasks_of_module(module.id)
                    ],
                )
                for module in loaded.modules
                if module.week_id == week.id
            ],
        )
        for week in loaded.weeks
    ]
    return ProgramRows(weeks)


def plan_text(loaded: Loaded) -> str:
    """Le plan courant en texte (modifications de January comprises), pour une révision."""
    lines: list[str] = []
    for week in loaded.weeks:
        lines.append(f"Semaine {week.rank} (du {week.start_date:%d/%m}) : {week.theme}")
        for module in (m for m in loaded.modules if m.week_id == week.id):
            if module.skipped:
                lines.append(f"  Module « {module.title} » : déjà acquis, sauté")
                continue
            lines.append(f"  Module « {module.title} »")
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
    """La différence de la dernière version, `None` pour la première (tout y est ajouté)."""
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
    """`(lundi à vendredi, samedi)` du budget de la version (minutes par jour)."""
    budget = (version.snapshot if version is not None else {}).get("budget", {})
    return int(budget.get("weekday_minutes", 0)), int(budget.get("weekend_minutes", 0))


async def _modules_out(db: AsyncSession, user_id: str, loaded: Loaded) -> dict[str, ModuleOut]:
    extras = ModuleExtrasRepository(db, user_id)
    rows = await extras.lessons(loaded.program.id)
    counts = await extras.resource_counts(loaded.program.id)
    open_ids = (
        await open_lesson_sessions(db, user_id, loaded.program.id)
        if any(row[1] == "generating" for row in rows.values())
        else []
    )
    # Leçon interrompue hors du port : montrée en échec, sans écriture (D91).
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
    return AppError("module_not_found", "Module introuvable.", 404)


async def program_of_module(db: AsyncSession, user_id: str, module_id: str) -> str:
    """Le programme d'un module de l'utilisateur ; 404 `module_not_found` s'il n'est pas à lui."""
    module = await ModuleRepository(db, user_id).get(module_id)
    if module is None:
        raise module_not_found()
    return module.program_id


async def list_validated_programs(db: AsyncSession) -> builtins.list[tuple[str, str]]:
    """`(utilisateur, programme)` des programmes validés de tous les utilisateurs : lecture sans
    `user_id` réservée à la tâche planifiée des leçons (D91), identifiants seulement."""
    return await validated_programs(db)
