"""Les écritures récentes des agents en mémoire, pour le fil d'activité (8.7). Lecture pour les
autres features (contrat 2) : le journal d'écriture, jamais le texte de l'élément."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.memory.repository import WriteRepository


@dataclass(frozen=True)
class AgentWrite:
    id: str
    item_id: str
    item_title: str
    action: str
    author: str  # le nom de l'agent (jamais `user`)
    reason: str | None
    at: datetime


async def recent_agent_writes(
    db: AsyncSession, user_id: str, after: datetime | None, before: datetime | None, limit: int
) -> list[AgentWrite]:
    """Les écritures des agents dans `]after, before[` (hors suppressions), la plus récente
    d'abord. Les écritures de l'utilisatrice n'y sont jamais."""
    rows = await WriteRepository(db, user_id).by_agents_between(after, before, limit)
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
