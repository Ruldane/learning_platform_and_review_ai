from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.features.brain.repository import SyncTokenRepository
from app.features.brain.schemas import BrainRelayStatus


async def connection(db: AsyncSession, user_id: str) -> BrainRelayStatus:
    contact = await SyncTokenRepository(db, user_id).contact()
    if contact is None:
        return BrainRelayStatus(state="unconfigured")
    (last_contact,) = contact
    if last_contact is None:
        return BrainRelayStatus(state="waiting")
    active = last_contact >= utcnow() - timedelta(minutes=10)
    return BrainRelayStatus(state="connected" if active else "offline", last_contact=last_contact)
