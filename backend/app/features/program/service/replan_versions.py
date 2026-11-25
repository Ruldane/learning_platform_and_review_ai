"""Versions of a replanning (SPEC F13, D106): proposal packed and stored (`save_proposal`),
acceptance (`apply_version`), refusal (`refuse_version`) and history.

Everything goes under `program_lock`, taken BEFORE opening the transaction (F4): an edit by
January and the acceptance of a proposal follow one another, never together. The proposal keeps
the fingerprint of the rows it packed (`base_fingerprint`) and what must be written
(`snapshot.changes`): accepted on rows that have moved, it is stale and nothing is written. An
empty proposal without an option or an impossible one is closed as soon as it is written
(`empty`, `impossible`), never `pending`. Logs: ids only."""

import logging
from collections.abc import Mapping, Sequence, Set
from dataclasses import dataclass, field, replace
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
from app.features.program.service.replan_gap import (
    LEGACY_NEW_GAP_MODULE,
    NEW_GAP_MODULE,
    gap_target,
    with_gap_module,
)
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
    return AppError("version_not_found", "Version not found.", 404)


@dataclass(frozen=True)
class Proposal:
    """What the Strategist proposes, references already resolved into ids by the port."""

    session_id: str
    revision: int
    reason: str
    drop: Set[str]
    add: Sequence[NewTask]
    option: ReplanOption | None
    week_cap_override: int | None
    review_entry_id: str | None
    today: date
    skills: Sequence[str] = ()  # `gap` trigger: skills of the postings module (D123)
    daily_caps: Mapping[date, int] = field(default_factory=dict)


async def program_budget(db: AsyncSession, user_id: str, loaded: Loaded) -> Budget:
    """The per-day budget of the applied plan (snapshot of its last version), otherwise that of
    the settings at the goal's scale."""
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
    rows = with_gap_module(rows_of(loaded), proposal.add)
    budget = replace(await program_budget(db, user_id, loaded), daily_caps=proposal.daily_caps)
    todo = {t.id for t in loaded.tasks if t.status == "todo"}
    modules = {m.id for m in loaded.modules if not m.skipped} | {
        NEW_GAP_MODULE,
        LEGACY_NEW_GAP_MODULE,
    }
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
    # Any new version, even a closed one, replaces the one that was waiting (D99, D106): no
    # proposal stays `pending` without a question waiting for it.
    await versions.supersede_pending(loaded.program.id)
    days = {"weekday_minutes": budget.weekday_minutes, "weekend_minutes": budget.weekend_minutes}
    changes = {**changes_json(result, finished=finished), "gap_skills": list(proposal.skills)}
    return await versions.add(
        program_id=loaded.program.id,
        version=await versions.next_version(loaded.program.id),
        snapshot={**after, "budget": days, "changes": changes},
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
    """Packs and stores the proposal (idempotent per `(session, revision)`); never
    `planning_impossible`: a closed `impossible` version. 404 if the program is another user's."""
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
    """Dates moved, tasks removed and added, "Continued" weeks and their module, "Postings
    skills" module (created or completed, D123)."""
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
    tasks = [PlannedTask.from_json(t) for t in raw.get("tasks", [])]
    gap_id = await gap_target(db, user_id, loaded, list(raw.get("gap_skills", [])), tasks)
    for task in tasks:
        if task.task_id:
            by_id[task.task_id].planned_date = task.planned_date
            continue
        module_id = task.module_id or suite_modules[task.suite_rank or 0]
        module_id = gap_id if module_id in (NEW_GAP_MODULE, LEGACY_NEW_GAP_MODULE) else module_id
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
    """Stale: no longer pending, rows changed since the proposal, or a day it would write has
    already passed (accepted too late)."""
    if row.status != "pending" or fingerprint(rows_of(loaded)) != row.base_fingerprint:
        return True
    first = earliest_date(row.snapshot.get("changes", {}))
    return first is not None and first < today


async def apply_version(
    rt: ProgramRuntime, user_id: str, program_id: str, version: int, now: datetime, today: date
) -> Applied:
    """Applies the proposal (see the module). Already accepted: returned without writing
    anything (replay); replaced, refused or closed, rows changed since the proposal, or a day
    to write before `today` (local day): `stale=True`, nothing is written. The program's other
    pending proposals become `superseded`."""
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
        "Replanning: user %s, program %s, version %d, stale %s",
        user_id,
        program_id,
        version,
        stale,
    )
    return Applied(version, stale=stale)


async def refuse_version(rt: ProgramRuntime, user_id: str, program_id: str, version: int) -> None:
    """The pending proposal becomes `refused`; otherwise nothing (idempotent)."""
    async with rt.program_lock(user_id, program_id), rt.session_factory() as db:
        row = await PlanVersionRepository(db, user_id).by_number(program_id, version)
        if row is None or row.kind != "replan":
            raise version_not_found()
        if row.status == "pending":
            row.status = "refused"
            await db.commit()


async def version_history(db: AsyncSession, user_id: str, program_id: str) -> list[PlanVersion]:
    """The program's versions, most recent first; 404 if it is another user's."""
    await load(db, user_id, program_id)
    return await PlanVersionRepository(db, user_id).history(program_id)
