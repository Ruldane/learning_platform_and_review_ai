"""In-memory state of the event bus: queue of each subscriber and state of each session.

Separated from `bus.py` (publication, subscription, end of session) so that each stays readable.
"""

import asyncio
from contextlib import suppress
from dataclasses import dataclass, field

from app.agents.runtime.events import SESSION_EVENT_ADAPTER, SessionEvent
from app.db.models.agents import SessionEventRecord


@dataclass(eq=False)
class Subscriber:
    """Queue of a subscriber; `None` in the queue signals the end of the session."""

    queue: asyncio.Queue[SessionEvent | None]
    overflowed: bool = False  # queue full: nothing else enters until the next replay
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
        with suppress(asyncio.QueueFull):  # queue full: `closed` is enough, seen once drained
            self.queue.put_nowait(None)

    async def next_live(self) -> SessionEvent | None:
        """Next event in the queue; `None` when it must replay (overflow) or finish."""
        if self.queue.empty() and (self.overflowed or self.closed):
            return None
        return await self.queue.get()


@dataclass(eq=False)
class SessionState:
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    last_seq: int | None = None  # None: to reread from the database
    subscribers: set[Subscriber] = field(default_factory=set)
    publishers: int = 0  # publications in progress or waiting for the lock
    closed: bool = False  # removed from the bus: a waiting publisher resumes with the new state


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
