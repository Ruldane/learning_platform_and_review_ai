from collections.abc import AsyncIterator, Callable
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.practice import content_version
from app.db.base import utcnow
from app.db.models.interprogram_planning import SharedWeekProposal
from app.features.calendar.service.runtime import CalendarRuntime
from app.features.interprogram_planning import planner, repository, sources
from app.features.interprogram_planning.schemas import (
    ProposalState,
    SharedWeekCreate,
    SharedWeekOption,
    SharedWeekOut,
    SharedWeekSnapshot,
)
from app.features.postings.service.runtime import KeyLocks
from app.features.program.service.runtime import ProgramRuntime


@dataclass
class SharedWeekRuntime:
    program: ProgramRuntime
    calendar: CalendarRuntime
    now: Callable[[], datetime] = utcnow
    locks: KeyLocks = field(default_factory=KeyLocks)


def _view(row: SharedWeekProposal) -> SharedWeekOut:
    draft = SharedWeekSnapshot.model_validate(row.document)
    status: ProposalState = "blocked" if draft.issues else "pending"
    if row.accepted_at is not None:
        status = "accepted"
    return SharedWeekOut(
        **draft.model_dump(),
        id=row.id,
        created_at=row.created_at,
        accepted_at=row.accepted_at,
        status=status,
    )


def _stamp(source: sources.WeekFacts, draft: SharedWeekSnapshot) -> str:
    return content_version(
        sources.fingerprint(source),
        [p.model_dump(mode="json") for p in draft.placements],
        draft.issues,
    )


async def options(db: AsyncSession, user_id: str) -> list[SharedWeekOption]:
    return [
        SharedWeekOption(id=program.id, title=program.title)
        for program in await repository.programs(db, user_id, only_validated=True)
    ]


async def list_proposals(db: AsyncSession, user_id: str) -> list[SharedWeekOut]:
    return [_view(row) for row in await repository.list_proposals(db, user_id)]


async def prepare(rt: SharedWeekRuntime, user_id: str, action: SharedWeekCreate) -> SharedWeekOut:
    programs = sorted(str(program_id) for program_id in action.program_ids)
    key = content_version(programs)
    async with rt.locks.get(user_id, "week"), rt.program.session_factory() as db:
        now = rt.now()
        facts = await sources.read(db, user_id, programs, action.week_start, now)
        draft = planner.prepare(facts, now)
        stamp = _stamp(facts, draft)
        if existing := await repository.existing(db, user_id, action.week_start, key, stamp):
            return _view(existing)
        row = SharedWeekProposal(
            user_id=user_id,
            week_start=action.week_start,
            selection_key=key,
            fingerprint=stamp,
            document=draft.model_dump(mode="json"),
        )
        db.add(row)
        await db.commit()
        return _view(row)


@asynccontextmanager
async def _apply_lock(rt: SharedWeekRuntime, user_id: str) -> AsyncIterator[None]:
    async with rt.locks.get(user_id, "week"), rt.calendar.lock(user_id):
        async with rt.program.session_factory() as db:
            program_ids = [row.id for row in await repository.programs(db, user_id)]
        async with AsyncExitStack() as stack:
            for program_id in sorted(program_ids):
                await stack.enter_async_context(rt.program.program_lock(user_id, program_id))
            yield


def _changed() -> AppError:
    return AppError(
        "shared_week_changed", "The constraints have changed. Prepare a new proposal.", 409
    )


async def _recheck(
    db: AsyncSession, user_id: str, row: SharedWeekProposal, draft: SharedWeekOut, now: datetime
) -> sources.WeekFacts:
    try:
        facts = await sources.read(
            db, user_id, [item.id for item in draft.programs], row.week_start, now
        )
    except AppError as error:
        if error.code in {
            "shared_week_past",
            "shared_week_program_not_validated",
            "program_not_found",
        }:
            raise _changed() from None
        raise
    current = planner.prepare(facts, now)
    if _stamp(facts, current) != row.fingerprint:
        raise _changed()
    return facts


async def accept(rt: SharedWeekRuntime, user_id: str, proposal_id: str) -> SharedWeekOut:
    async with _apply_lock(rt, user_id), rt.program.session_factory() as db:
        row = await repository.by_id(db, user_id, proposal_id)
        if row is None:
            raise AppError("shared_week_not_found", "Proposal not found.", 404)
        draft = _view(row)
        if draft.status == "accepted":
            return draft
        if draft.status == "blocked":
            raise AppError("shared_week_blocked", "The proposal cannot be applied.", 409)
        now = rt.now()
        facts = await _recheck(db, user_id, row, draft, now)
        tasks = {task.id: task for task in facts.scheduled}
        for placement in draft.placements:
            tasks[placement.task_id].planned_date = placement.planned_date
        row.accepted_at = now
        await db.commit()
        return _view(row)
