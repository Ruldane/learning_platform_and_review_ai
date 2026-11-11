"""État mémoire du bus d'événements : file de chaque abonné et état de chaque session.

Séparé de `bus.py` (publication, abonnement, fin de session) pour que chacun reste lisible.
"""

import asyncio
from contextlib import suppress
from dataclasses import dataclass, field

from app.agents.runtime.events import SESSION_EVENT_ADAPTER, SessionEvent
from app.db.models.agents import SessionEventRecord


@dataclass(eq=False)
class Subscriber:
    """File d'un abonné ; `None` en file signale la fin de la session."""

    queue: asyncio.Queue[SessionEvent | None]
    overflowed: bool = False  # file pleine : plus rien n'y entre jusqu'au prochain rejeu
    closed: bool = False

    def offer(self, event: SessionEvent) -> None:
        if self.overflowed:
            return
        try:
            self.queue.put_nowait(event)
        except asyncio.QueueFull:
            self.overflowed = True

    def close(self) -> None:
        self.closed = True
        with suppress(asyncio.QueueFull):  # file pleine : `closed` suffit, vue une fois vidée
            self.queue.put_nowait(None)

    async def next_live(self) -> SessionEvent | None:
        """Prochain événement en file ; `None` quand il faut rejouer (débordement) ou finir."""
        if self.queue.empty() and (self.overflowed or self.closed):
            return None
        return await self.queue.get()


@dataclass(eq=False)
class SessionState:
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    last_seq: int | None = None  # None : à relire en base
    subscribers: set[Subscriber] = field(default_factory=set)
    publishers: int = 0  # publications en cours ou en attente du verrou
    closed: bool = False  # retiré du bus : un publieur en attente reprend avec le nouvel état


def to_event(row: SessionEventRecord) -> SessionEvent:
    return SESSION_EVENT_ADAPTER.validate_python(
        {
            "id": row.id,
            "session_id": row.session_id,
            "seq": row.seq,
            "ts": row.created_at,
            "type": row.type,
            "agent": row.agent,
            "payload": row.payload,
        }
    )
