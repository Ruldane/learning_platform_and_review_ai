from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.dated_commitments import DatedCommitment


async def by_id(db: AsyncSession, user_id: str, item_id: str) -> DatedCommitment | None:
    return await db.scalar(
        select(DatedCommitment).where(
            DatedCommitment.user_id == user_id, DatedCommitment.id == item_id
        )
    )


async def by_request(db: AsyncSession, user_id: str, request_id: str) -> DatedCommitment | None:
    return await db.scalar(
        select(DatedCommitment).where(
            DatedCommitment.user_id == user_id, DatedCommitment.request_id == request_id
        )
    )


async def list_for_user(db: AsyncSession, user_id: str) -> list[DatedCommitment]:
    stmt = (
        select(DatedCommitment)
        .where(DatedCommitment.user_id == user_id)
        .order_by(DatedCommitment.due_on.desc(), DatedCommitment.id)
    )
    return list(await db.scalars(stmt))


async def reminders(
    db: AsyncSession, user_id: str, today: date, limit: int
) -> list[DatedCommitment]:
    eligible = select(DatedCommitment).where(
        DatedCommitment.user_id == user_id, DatedCommitment.due_on <= today
    )
    measured = (
        eligible.where(DatedCommitment.reviewed_on.between(today - timedelta(days=1), today))
        .order_by(DatedCommitment.reviewed_at.desc(), DatedCommitment.id)
        .limit(limit)
    )
    recent = list(await db.scalars(measured))
    open_items = (
        eligible.where(DatedCommitment.reviewed_on.is_(None))
        .order_by(DatedCommitment.due_on, DatedCommitment.id)
        .limit(limit - int(bool(recent)))
    )
    outstanding = list(await db.scalars(open_items))
    return [*outstanding, *recent[: limit - len(outstanding)]]
