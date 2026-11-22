"""Services du contrôle de transfert et de son agent."""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.skill_transfer.repository import Transfers


async def count_due_transfers(db: AsyncSession, user_id: str, day: date) -> int:
    return await Transfers(db, user_id).count_due(day)
