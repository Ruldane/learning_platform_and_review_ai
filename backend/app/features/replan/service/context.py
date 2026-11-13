"""Contexte d'une replanification (port `ReplanStore.context`, D105, D106) : le programme validé
de January, son bilan (et les options qu'il offre), son budget et le plan à faire par références.

Les références sont stables dans un instantané : `m1…` pour les modules non sautés dans l'ordre
du programme, `t1…` pour toutes les tâches à faire, par jour puis par ordre du programme (les
retards en tête : `late`, datées avant aujourd'hui). Les ids ne vont jamais au modèle (F7)."""

from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.program_port import BudgetView
from app.agents.tools.replan_port import ModuleRef, ReplanContext, ReviewView, TaskRef, week_cap
from app.agents.tools.study_schema import ReplanTrigger, ReviewState
from app.core.errors import AppError
from app.features.learning.service.goals import owned_goal
from app.features.program.service.programs import Loaded, load
from app.features.program.service.replan_versions import program_budget
from app.features.program.service.rules import floor_minutes
from app.features.replan.repository import ReviewRepository
from app.features.replan.service.review import options_for

STATES: tuple[ReviewState, ...] = ("late_twice", "late", "ahead", "on_track")


def program_not_validated() -> AppError:
    return AppError(
        "program_not_validated", "Valide d'abord ton programme pour le replanifier.", 409
    )


def review_not_found() -> AppError:
    return AppError("review_not_found", "Bilan introuvable.", 404)


async def _review(
    db: AsyncSession, user_id: str, program_id: str, entry_id: str | None
) -> ReviewView:
    entry = await ReviewRepository(db, user_id).review(entry_id or "")
    data = entry.data if entry is not None else {}
    state = next((s for s in STATES if s == data.get("state")), None)
    if entry is None or data.get("program_id") != program_id or state is None:
        raise review_not_found()
    week = date.fromisoformat(str(data["week_start"]))
    return ReviewView(entry.id, week, entry.text, state, float(data.get("ratio", 0.0)))


def _refs(loaded: Loaded, today: date) -> tuple[list[ModuleRef], list[TaskRef]]:
    modules = [m for m in loaded.modules if not m.skipped]
    refs = {m.id: f"m{n}" for n, m in enumerate(modules, start=1)}
    order = {t.id: n for n, t in enumerate(loaded.tasks)}
    todo = sorted(
        (t for t in loaded.tasks if t.status == "todo" and t.module_id in refs),
        key=lambda t: (t.planned_date, order[t.id]),
    )
    module_refs = [
        ModuleRef(refs[m.id], m.title, [str(s) for s in m.skills], m.id) for m in modules
    ]
    task_refs = [
        TaskRef(
            f"t{n}",
            t.title,
            t.type,  # type: ignore[arg-type]  # colonne texte, valeurs de TaskType
            t.minutes,
            t.planned_date,
            refs[t.module_id],
            t.planned_date < today,
            t.id,
        )
        for n, t in enumerate(todo, start=1)
    ]
    return module_refs, task_refs


async def build_context(
    db: AsyncSession,
    user_id: str,
    program_id: str,
    *,
    today: date,
    trigger: ReplanTrigger,
    review_entry_id: str | None,
    available_minutes: int | None,
    message: str | None,
) -> ReplanContext:
    """404 `program_not_found` (programme d'un autre), 409 `program_not_validated`, 404
    `review_not_found` (bilan d'un autre programme ou d'un autre utilisateur)."""
    loaded = await load(db, user_id, program_id)
    program = loaded.program
    if program.status != "validated":
        raise program_not_validated()
    review = None
    if trigger == "weekly_review":
        review = await _review(db, user_id, program_id, review_entry_id)
    budget = await program_budget(db, user_id, loaded)
    goal = await owned_goal(db, user_id, program.goal_id)
    modules, tasks = _refs(loaded, today)
    deadline = loaded.weeks[-1].start_date + timedelta(days=6) if loaded.weeks else None
    return ReplanContext(
        program_id=program_id,
        title=program.title,
        goal=goal.text,
        deadline=deadline,
        budget=BudgetView(
            budget.weekly_minutes,
            budget.cap_minutes,
            budget.weekday_minutes,
            budget.weekend_minutes,
            floor_minutes(budget.cap_minutes),
        ),
        review=review,
        options=options_for(review.state) if review is not None else (),
        modules=modules,
        tasks=tasks,
        week_cap_override=week_cap(available_minutes) if available_minutes else None,
        message=message,
    )
