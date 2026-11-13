"""Versions d'une replanification (SPEC F13, D106) : proposition rangée et enregistrée
(`save_proposal`), acceptation (`apply_version`), refus (`refuse_version`) et historique.

Tout passe sous `program_lock`, pris AVANT d'ouvrir la transaction (F4) : une modification de
January et l'acceptation d'une proposition se suivent, jamais ensemble. La proposition garde
l'empreinte des lignes qu'elle a rangées (`base_fingerprint`) et ce qu'il faut écrire
(`snapshot.changes`) : acceptée sur des lignes qui ont bougé, elle est périmée et rien n'est
écrit. Une proposition vide sans option ou impossible est close dès son écriture (`empty`,
`impossible`), jamais `pending`. Journaux : identifiants seulement."""

import logging
from collections.abc import Sequence, Set
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.replan_port import Applied, PreviewSaved
from app.agents.tools.study_schema import ReplanOption
from app.core.errors import AppError
from app.db.models.program import PlanVersion
from app.features.learning.service.goals import owned_goal
from app.features.program.repository import (
    ModuleRepository,
    PlanVersionRepository,
    TaskRepository,
    WeekRepository,
)
from app.features.program.service.budget import Budget
from app.features.program.service.diff import PlanDiff, diff_plans, snapshot
from app.features.program.service.drafting import budget_of
from app.features.program.service.planning import PlanningImpossible
from app.features.program.service.programs import Loaded, day_budget, load, rows_of
from app.features.program.service.replan_json import (
    changes_json,
    earliest_date,
    loads_json,
    saved_of,
)
from app.features.program.service.replan_rows import NewTask, NewWeek, PlannedTask, after_rows
from app.features.program.service.replanning import (
    ProgramFinished,
    RepackResult,
    fingerprint,
    repack,
)
from app.features.program.service.runtime import ProgramRuntime

logger = logging.getLogger(__name__)


def version_not_found() -> AppError:
    return AppError("version_not_found", "Version introuvable.", 404)


@dataclass(frozen=True)
class Proposal:
    """Ce que le Stratège propose, références déjà résolues en ids par le port."""

    session_id: str
    revision: int
    reason: str
    drop: Set[str]
    add: Sequence[NewTask]
    option: ReplanOption | None
    week_cap_override: int | None
    review_entry_id: str | None
    today: date


async def program_budget(db: AsyncSession, user_id: str, loaded: Loaded) -> Budget:
    """Le budget par jour du plan appliqué (instantané de sa dernière version), sinon celui des
    réglages à l'échelle de l'objectif."""
    latest = await PlanVersionRepository(db, user_id).latest(loaded.program.id)
    weekday, weekend = day_budget(latest)
    if weekday or weekend:
        return Budget(weekday, weekend)
    goal = await owned_goal(db, user_id, loaded.program.goal_id)
    return await budget_of(db, user_id, goal.weekly_minutes)


def _status(result: RepackResult | None, diff: PlanDiff, option: ReplanOption | None) -> str:
    if result is None:
        return "impossible"
    changed = diff.added or diff.removed or diff.moved or result.new_weeks
    return "pending" if changed or option is not None else "empty"


async def _write_proposal(
    db: AsyncSession, user_id: str, loaded: Loaded, proposal: Proposal
) -> PlanVersion:
    rows = rows_of(loaded)
    budget = await program_budget(db, user_id, loaded)
    todo = {t.id for t in loaded.tasks if t.status == "todo"}
    modules = {m.id for m in loaded.modules if not m.skipped}
    try:
        result: RepackResult | None = repack(
            rows,
            budget,
            today=proposal.today,
            drop={i for i in proposal.drop if i in todo},
            add=[t for t in proposal.add if t.module_id in modules],
            option=proposal.option,
            week_cap_override=proposal.week_cap_override,
        )
    except PlanningImpossible as exc:
        result, finished = None, isinstance(exc, ProgramFinished)
    else:
        finished = False
    before = snapshot(rows)
    after = before
    if result is not None:
        after = snapshot(after_rows(rows, result.tasks, result.removed, result.new_weeks))
    diff = diff_plans(before, after)
    status = _status(result, diff, proposal.option)
    versions = PlanVersionRepository(db, user_id)
    # Toute nouvelle version, même close, remplace celle qui attendait (D99, D106) : aucune
    # proposition ne reste `pending` sans question qui l'attende.
    await versions.supersede_pending(loaded.program.id)
    days = {"weekday_minutes": budget.weekday_minutes, "weekend_minutes": budget.weekend_minutes}
    return await versions.add(
        program_id=loaded.program.id,
        version=await versions.next_version(loaded.program.id),
        snapshot={**after, "budget": days, "changes": changes_json(result, finished=finished)},
        diff=diff.to_json(),
        reason=proposal.reason[:300],
        session_id=proposal.session_id,
        revision=proposal.revision,
        kind="replan",
        status=status,
        base_fingerprint=fingerprint(rows),
        review_entry_id=proposal.review_entry_id,
        week_loads=loads_json(result, result.kept if result is not None else 0),
    )


async def save_proposal(
    rt: ProgramRuntime, user_id: str, program_id: str, proposal: Proposal
) -> PreviewSaved:
    """Range et enregistre la proposition (idempotent par `(session, revision)`) ; jamais
    `planning_impossible` : une version close `impossible`. 404 si le programme est à un autre."""
    async with rt.program_lock(user_id, program_id), rt.session_factory() as db:
        found = await PlanVersionRepository(db, user_id).by_revision(
            proposal.session_id, proposal.revision
        )
        if found is not None:
            return saved_of(found)
        version = await _write_proposal(db, user_id, await load(db, user_id, program_id), proposal)
        saved = saved_of(version)
        status = version.status
        await db.commit()
    logger.info(
        "Proposition de replanification : utilisateur %s, programme %s, version %d, %s",
        user_id,
        program_id,
        saved.version,
        status,
    )
    return saved


async def _write_changes(db: AsyncSession, user_id: str, loaded: Loaded, raw: Any) -> None:
    """Dates déplacées, tâches retirées et ajoutées, semaines « Suite » et leur module."""
    tasks_repo = TaskRepository(db, user_id)
    program_id = loaded.program.id
    suite_modules: dict[int, str] = {}
    for week in (NewWeek.from_json(w) for w in raw.get("new_weeks", [])):
        row = await WeekRepository(db, user_id).add(
            program_id=program_id,
            rank=week.rank,
            theme=week.theme,
            objective=week.objective,
            deliverable=week.deliverable,
            start_date=week.start_date,
        )
        module = await ModuleRepository(db, user_id).add(
            week_id=row.id, program_id=program_id, rank=0, title=week.theme, skills=[]
        )
        suite_modules[week.rank] = module.id
    by_id = {t.id: t for t in loaded.tasks}
    for task in (PlannedTask.from_json(t) for t in raw.get("tasks", [])):
        if task.task_id:
            by_id[task.task_id].planned_date = task.planned_date
            continue
        module_id = task.module_id or suite_modules[task.suite_rank or 0]
        await tasks_repo.add(
            module_id=module_id,
            program_id=program_id,
            rank=await tasks_repo.next_rank(module_id),
            title=task.title,
            type=task.type,
            minutes=task.minutes,
            done_criterion=task.done_criterion,
            planned_date=task.planned_date,
            status="todo",
        )
    await tasks_repo.delete_many(list(raw.get("removed", [])))


def _outdated(row: PlanVersion, loaded: Loaded, today: date) -> bool:
    """Périmée : plus en attente, lignes changées depuis la proposition, ou un jour qu'elle
    écrirait est déjà passé (acceptée trop tard)."""
    if row.status != "pending" or fingerprint(rows_of(loaded)) != row.base_fingerprint:
        return True
    first = earliest_date(row.snapshot.get("changes", {}))
    return first is not None and first < today


async def apply_version(
    rt: ProgramRuntime, user_id: str, program_id: str, version: int, now: datetime, today: date
) -> Applied:
    """Applique la proposition (voir le module). Déjà acceptée : rendue sans rien écrire (rejeu) ;
    remplacée, refusée ou close, lignes changées depuis la proposition, ou un jour à écrire
    avant `today` (jour local) : `stale=True`, rien n'est écrit. Les autres propositions en
    attente du programme passent `superseded`."""
    async with rt.program_lock(user_id, program_id), rt.session_factory() as db:
        versions = PlanVersionRepository(db, user_id)
        row = await versions.by_number(program_id, version)
        if row is None or row.kind != "replan":
            raise version_not_found()
        if row.status == "accepted":
            return Applied(version, stale=False)
        loaded = await load(db, user_id, program_id)
        if _outdated(row, loaded, today):
            stale = True
        else:
            await _write_changes(db, user_id, loaded, row.snapshot.get("changes", {}))
            await versions.supersede_pending(program_id, keep=row.id)
            row.status, row.accepted_at = "accepted", now
            loaded.program.version = row.version
            await db.commit()
            stale = False
    logger.info(
        "Replanification : utilisateur %s, programme %s, version %d, périmée %s",
        user_id,
        program_id,
        version,
        stale,
    )
    return Applied(version, stale=stale)


async def refuse_version(rt: ProgramRuntime, user_id: str, program_id: str, version: int) -> None:
    """La proposition en attente devient `refused` ; sinon rien (idempotent)."""
    async with rt.program_lock(user_id, program_id), rt.session_factory() as db:
        row = await PlanVersionRepository(db, user_id).by_number(program_id, version)
        if row is None or row.kind != "replan":
            raise version_not_found()
        if row.status == "pending":
            row.status = "refused"
            await db.commit()


async def version_history(db: AsyncSession, user_id: str, program_id: str) -> list[PlanVersion]:
    """Les versions du programme, la plus récente d'abord ; 404 s'il est à un autre."""
    await load(db, user_id, program_id)
    return await PlanVersionRepository(db, user_id).history(program_id)
