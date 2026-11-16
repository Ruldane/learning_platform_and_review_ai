"""Les écritures récentes des agents en mémoire, pour le fil d'activité (8.7). Lecture pour les
autres features (contrat 2) : le journal d'écriture, jamais le texte de l'élément."""

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
    author: str  # le nom de l'agent (jamais `user`)
    reason: str | None
    at: datetime


async def recent_agent_writes(
    db: AsyncSession, user_id: str, after: datetime | None, before: datetime | None, limit: int
) -> list[AgentWrite]:
    """Les écritures des agents dans `[after, before]` (bornes incluses, hors suppressions), la
    plus récente d'abord. N'y sont jamais : les écritures de l'utilisatrice, ni celles de sa propre
    capture rapide (l'Archiviste les écrit sur sa demande : raison `CAPTURE_REASON`, ou acquis
    reflétés par la capture), reconnues à leur auteur et à leur raison."""
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
