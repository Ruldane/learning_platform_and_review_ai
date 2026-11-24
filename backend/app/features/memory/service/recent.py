"""Recent agent writes to memory, for the activity feed (8.7). Read access for other
features (contract 2): the write log, never the item's text."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.memory.repository import WriteRepository
from app.features.memory.service.captured import (
    CAPTURE_AUTHOR,
    CAPTURE_REASON,
    CAPTURE_REFLECT_PREFIX,
)


@dataclass(frozen=True)
class AgentWrite:
    id: str
    item_id: str
    item_title: str
    action: str
    author: str  # the agent's name (never `user`)
    reason: str | None
    at: datetime


async def recent_agent_writes(
    db: AsyncSession, user_id: str, after: datetime | None, before: datetime | None, limit: int
) -> list[AgentWrite]:
    """Agent writes within `[after, before]` (inclusive bounds, deletions excluded), most
    recent first. Never included: the user's own writes, nor those of her quick capture (the
    Archivist writes them at her request: reason `CAPTURE_REASON`, or skills reflected by the
    capture), recognised by their author and reason."""
    skip = (CAPTURE_AUTHOR, CAPTURE_REASON, CAPTURE_REFLECT_PREFIX)
    rows = await WriteRepository(db, user_id).by_agents_between(after, before, limit, skip=skip)
    return [
        AgentWrite(
            id=row.id,
            item_id=row.item_id,
            item_title=row.item_title,
            action=row.action,
            author=row.author,
            reason=row.reason,
            at=row.created_at,
        )
        for row in rows
    ]
