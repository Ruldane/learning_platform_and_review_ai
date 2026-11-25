"""Writing an event through the bus; the session lock is held by the caller (`bus.py`).

- Numbering: `seq` = last known + 1 (cache `SessionState.last_seq`, initialized by
  `max_seq`). The `(session_id, seq)` uniqueness in the database remains the safety net: a `seq`
  refused (writer outside the bus) makes `max_seq` be reread and the WHOLE transaction replayed.
- Optional guard (`publish_with`, D61): called inside the event's transaction, before
  the insert. `False`: rollback, nothing is written. `True`: the event is inserted in the
  same transaction, then everything is committed at once; if the insert or the commit
  fails, what the guard wrote is rolled back with it (never a final status without its
  event, D52 §2). The guard must start with its write (no read before): SQLite then
  applies the lock wait timeout instead of failing.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.bus_state import SessionState
from app.agents.runtime.repositories import EventRepository, SessionRepository
from app.core.errors import AppError
from app.db.models.agents import SessionEventRecord

type Guard = Callable[[AsyncSession], Awaitable[bool]]

_WRITE_ATTEMPTS = 3


class EventWriter:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def write(
        self,
        state: SessionState,
        user_id: str,
        session_id: str,
        type: str,
        data: dict[str, Any],
        agent: str | None,
        guard: Guard | None = None,
    ) -> SessionEventRecord | None:
        """Numbers and writes; `None` if the guard refuses (nothing written, cache intact). Any
        error other than a refused `seq` invalidates the cache: the database decides next time."""
        attempt = 0
        while True:
            attempt += 1
            if state.last_seq is None:
                state.last_seq = await self.load_last_seq(user_id, session_id)
            seq = state.last_seq + 1
            try:
                row = await self.insert(user_id, session_id, seq, type, data, agent, guard)
            except IntegrityError:
                state.last_seq = None
                if attempt >= _WRITE_ATTEMPTS:
                    raise
                continue
            except BaseException:
                state.last_seq = None  # unknown outcome (committed or not)
                raise
            if row is not None:
                state.last_seq = seq
            return row

    async def load_last_seq(self, user_id: str, session_id: str) -> int:
        # Read in its own transaction: the write that follows starts with a write
        # (guard or INSERT), so SQLite applies the lock wait timeout instead of failing.
        async with self._factory() as db:
            if await SessionRepository(db, user_id).get(session_id) is None:
                raise AppError("session_not_found", "Session not found.", status_code=404)
            return await EventRepository(db, user_id).max_seq(session_id)

    async def insert(
        self,
        user_id: str,
        session_id: str,
        seq: int,
        type: str,
        data: dict[str, Any],
        agent: str | None,
        guard: Guard | None = None,
    ) -> SessionEventRecord | None:
        async with self._factory() as db:
            if guard is not None and not await guard(db):
                await db.rollback()
                return None
            row = await EventRepository(db, user_id).add(
                session_id=session_id, seq=seq, type=type, agent=agent, payload=data
            )
            await db.commit()
        return row
