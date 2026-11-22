from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.missions import Mission


async def by_id(db: AsyncSession, user_id: str, mission_id: str) -> Mission | None:
    return await db.scalar(
        select(Mission).where(Mission.user_id == user_id, Mission.id == mission_id)
    )


async def by_posting(db: AsyncSession, user_id: str, posting_id: str) -> Mission | None:
    return await db.scalar(
        select(Mission).where(Mission.user_id == user_id, Mission.posting_id == posting_id)
    )


async def list_for_user(db: AsyncSession, user_id: str) -> list[Mission]:
    return list(
        await db.scalars(
            select(Mission)
            .where(Mission.user_id == user_id)
            .order_by(Mission.created_at.desc(), Mission.id.desc())
        )
    )
