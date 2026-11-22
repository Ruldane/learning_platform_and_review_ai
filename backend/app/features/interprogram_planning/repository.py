from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.calendar import CalendarProposal
from app.db.models.interprogram_planning import SharedWeekProposal
from app.db.models.program import Program, Task


async def list_proposals(db: AsyncSession, user_id: str) -> list[SharedWeekProposal]:
    stmt = (
        select(SharedWeekProposal)
        .where(SharedWeekProposal.user_id == user_id)
        .order_by(SharedWeekProposal.created_at.desc(), SharedWeekProposal.id.desc())
    )
    return list(await db.scalars(stmt))


async def by_id(db: AsyncSession, user_id: str, proposal_id: str) -> SharedWeekProposal | None:
    return await db.scalar(
        select(SharedWeekProposal).where(
            SharedWeekProposal.user_id == user_id,
            SharedWeekProposal.id == proposal_id,
        )
    )


async def existing(
    db: AsyncSession, user_id: str, week_start: date, key: str, fingerprint: str
) -> SharedWeekProposal | None:
    return await db.scalar(
        select(SharedWeekProposal).where(
            SharedWeekProposal.user_id == user_id,
            SharedWeekProposal.week_start == week_start,
            SharedWeekProposal.selection_key == key,
            SharedWeekProposal.fingerprint == fingerprint,
        )
    )


async def programs(
    db: AsyncSession, user_id: str, *, only_validated: bool = False
) -> list[Program]:
    stmt = select(Program).where(Program.user_id == user_id).order_by(Program.id)
    if only_validated:
        stmt = stmt.where(Program.status == "validated")
    return list(await db.scalars(stmt))


async def week_tasks(db: AsyncSession, user_id: str, start: date, end: date) -> list[Task]:
    stmt = (
        select(Task)
        .join(Program, Program.id == Task.program_id)
        .where(
            Task.user_id == user_id,
            Program.user_id == user_id,
            Program.status == "validated",
            Task.planned_date >= start,
            Task.planned_date < end,
        )
        .order_by(Task.id)
    )
    return list(await db.scalars(stmt))


async def bookings(
    db: AsyncSession, user_id: str, earliest: datetime, latest: datetime
) -> list[CalendarProposal]:
    stmt = (
        select(CalendarProposal)
        .where(
            CalendarProposal.user_id == user_id,
            CalendarProposal.synced_at.is_not(None),
            CalendarProposal.starts_at >= earliest,
            CalendarProposal.starts_at < latest,
        )
        .order_by(CalendarProposal.starts_at, CalendarProposal.id)
    )
    return list(await db.scalars(stmt))
