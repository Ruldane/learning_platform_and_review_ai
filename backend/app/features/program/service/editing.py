"""Modifications de January sur un programme (SPEC 3.4, D88) : déplacer ou retoucher une tâche,
ajouter et supprimer des tâches, décaler la date de début d'un brouillon.

Tout se fait sous `program_lock(user_id, program_id)`, sur l'état relu dans une session neuve :
les règles de la semaine (85 % du budget, au moins une pratique, un quiz) sont vérifiées sur
chaque semaine touchée avant le commit. Deux déplacements qui tiennent chacun mais pas ensemble :
le second voit le premier et reçoit une 422 lisible, sans recopie de la saisie."""

import logging
from collections.abc import Iterable
from datetime import timedelta

from app.core.errors import AppError
from app.db.models.program import Task, Week
from app.features.program.repository import TaskRepository
from app.features.program.schemas import ProgramOut, ProgramPatch, TaskOut, TaskPatch
from app.features.program.service.programs import Loaded, load, task_out, view_of
from app.features.program.service.runtime import ProgramRuntime

logger = logging.getLogger(__name__)

MONDAY = 0


class WeekRuleBroken(AppError):
    """Une règle de la semaine serait cassée ; `details` : rang, charge et plafond (nombres)."""

    def __init__(
        self, code: str, message: str, week: Week | None, planned: int | None, cap: int
    ) -> None:
        details = {
            "week_rank": week.rank if week is not None else None,
            "planned_minutes": planned,
            "cap_minutes": cap,
        }
        super().__init__(code, message, 422, details)


def task_not_found() -> AppError:
    return AppError("task_not_found", "Tâche introuvable.", 404)


def module_not_found() -> AppError:
    return AppError("module_not_found", "Module introuvable.", 404)


def _outside(cap: int) -> WeekRuleBroken:
    return WeekRuleBroken(
        "date_outside_program", "Ce jour est en dehors des semaines du programme.", None, None, cap
    )


def check_weeks(loaded: Loaded, weeks: Iterable[Week | None]) -> None:
    """Règles de chaque semaine donnée, sur les tâches planifiées dans ses sept jours (la même
    règle que `planning.week_problems`) : la première cassée lève `WeekRuleBroken`."""
    cap = loaded.program.cap_minutes
    for week in sorted({w for w in weeks if w is not None}, key=lambda w: w.rank):
        tasks = [t for t in loaded.tasks if loaded.week_of(t.planned_date) is week]
        total = sum(t.minutes for t in tasks)
        label = f"La semaine {week.rank}"
        if total > cap:
            message = (
                f"{label} dépasserait 85 % de ton budget : {total} min prévues, {cap} au plus."
            )
            raise WeekRuleBroken("week_over_budget", message, week, total, cap)
        if not any(t.type == "pratiquer" for t in tasks):
            message = f"{label} doit garder au moins une tâche de pratique."
            raise WeekRuleBroken("week_needs_practice", message, week, total, cap)
        if not any(t.type == "quiz" for t in tasks):
            message = f"{label} doit garder son quiz."
            raise WeekRuleBroken("week_needs_quiz", message, week, total, cap)


def _apply(loaded: Loaded, task: Task, patch: TaskPatch) -> set[Week | None]:
    """Applique la retouche ; rend les semaines touchées (charge ou type changés)."""
    touched: set[Week | None] = set()
    if patch.planned_date is not None and patch.planned_date != task.planned_date:
        target = loaded.week_of(patch.planned_date)
        if target is None:
            raise _outside(loaded.program.cap_minutes)
        touched |= {loaded.week_of(task.planned_date), target}
        task.planned_date = patch.planned_date
    if patch.minutes is not None and patch.minutes != task.minutes:
        task.minutes = patch.minutes
        touched.add(loaded.week_of(task.planned_date))
    if patch.title is not None:
        task.title = patch.title
    if patch.status is not None:
        task.status = patch.status
    return touched


async def move_or_edit_task(
    rt: ProgramRuntime, user_id: str, task_id: str, patch: TaskPatch
) -> TaskOut:
    """Déplace ou retouche une tâche (jour, durée, titre, statut) sous le verrou du programme."""
    async with rt.session_factory() as db:
        program_id = await TaskRepository(db, user_id).program_of(task_id)
    if program_id is None:
        raise task_not_found()
    async with rt.program_lock(user_id, program_id), rt.session_factory() as db:
        loaded = await load(db, user_id, program_id)
        task = next((t for t in loaded.tasks if t.id == task_id), None)
        if task is None:
            raise task_not_found()
        check_weeks(loaded, _apply(loaded, task, patch))
        await db.commit()
        out = task_out(task)
    logger.info(
        "Tâche modifiée : utilisateur %s, programme %s, tâche %s", user_id, program_id, task_id
    )
    return out


def _shift(loaded: Loaded, patch: ProgramPatch) -> None:
    """Décale tout le brouillon (semaines et tâches) à une nouvelle date de début, un lundi."""
    program, start = loaded.program, patch.start_date
    if start is None or start == program.start_date:
        return
    if program.status != "draft":
        raise AppError(
            "program_validated", "La date de début d'un programme validé ne change plus.", 409
        )
    if start.weekday() != MONDAY:
        raise AppError(
            "invalid_start_date", "Un programme commence un lundi.", 422, {"fields": ["start_date"]}
        )
    delta: timedelta = start - program.start_date
    for week in loaded.weeks:
        week.start_date += delta
    for task in loaded.tasks:
        task.planned_date += delta
    program.start_date = start


async def _delete(loaded: Loaded, repo: TaskRepository, ids: list[str]) -> set[Week | None]:
    by_id = {task.id: task for task in loaded.tasks}
    if any(task_id not in by_id for task_id in ids):
        raise task_not_found()
    touched = {loaded.week_of(by_id[task_id].planned_date) for task_id in ids}
    await repo.delete_many(ids)
    loaded.tasks = [task for task in loaded.tasks if task.id not in set(ids)]
    return touched


async def _add(loaded: Loaded, repo: TaskRepository, patch: ProgramPatch) -> set[Week | None]:
    modules = {m.id: m for m in loaded.modules if not m.skipped}
    touched: set[Week | None] = set()
    for new in patch.add_tasks:
        if new.module_id not in modules:
            raise module_not_found()
        week = loaded.week_of(new.planned_date)
        if week is None:
            raise _outside(loaded.program.cap_minutes)
        task = await repo.add(
            **new.model_dump(),
            program_id=loaded.program.id,
            rank=await repo.next_rank(new.module_id),
            status="todo",
            already_known=False,
        )
        loaded.tasks.append(task)
        touched.add(week)
    return touched


async def add_and_delete(
    rt: ProgramRuntime, user_id: str, program_id: str, patch: ProgramPatch
) -> ProgramOut:
    """Date de début (brouillon), suppressions puis ajouts, appliqués ensemble sous le verrou :
    une règle cassée annule tout (rien n'est commité)."""
    async with rt.program_lock(user_id, program_id), rt.session_factory() as db:
        loaded = await load(db, user_id, program_id)
        repo = TaskRepository(db, user_id)
        _shift(loaded, patch)
        touched = await _delete(loaded, repo, list(dict.fromkeys(patch.delete_task_ids)))
        touched |= await _add(loaded, repo, patch)
        check_weeks(loaded, touched)
        await db.commit()
        view = await view_of(db, user_id, loaded)
    logger.info(
        "Programme modifié : utilisateur %s, programme %s, %d ajout(s), %d suppression(s)",
        user_id,
        program_id,
        len(patch.add_tasks),
        len(patch.delete_task_ids),
    )
    return view
