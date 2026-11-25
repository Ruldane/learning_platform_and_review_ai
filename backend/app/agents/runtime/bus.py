"""Event bus of a session: writes each event into `session_events`, then broadcasts it.

- `publish` validates the payload against the catalogue (fields outside the catalogue are
  dropped: nothing unexpected, a key for example, is written or broadcast), then, under a lock
  of its own to the session, numbers it (`seq` = last known + 1, cache initialised by `max_seq`),
  writes and commits the row, and pushes it onto the queue of each subscriber: the order of the
  queues is that of the `seq`. The `(session_id, seq)` uniqueness in the database stays the
  safety net (stale cache: we read again). The write itself lives in `bus_write.py`.
- `publish_with` adds a guard run inside the event's transaction: the outcome of a session
  (final status) and its event are committed together, or not at all (D61).
- `subscribe` registers its queue BEFORE any read, replays the database after `after_seq`, then
  switches to live, ignoring any `seq` already emitted: no gap, no duplicate.
- Bounded queue: when full, it stops receiving; its subscriber empties it then goes back
  through the replay. Likewise if the live feed skips a number (writer outside the bus): replay
  from the last one received.
- `flush` waits for the protected writes in flight, of all sessions or of a single one (N5);
  `aclose` (server shutdown) waits for all of them.

One bus per process (`app.state`): the live broadcast is in memory.
"""

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.bus_state import SessionState, Subscriber, to_event
from app.agents.runtime.bus_write import EventWriter, Guard
from app.agents.runtime.events import EventType, SessionEvent, validate_payload
from app.agents.runtime.repositories import EventRepository

__all__ = ["EventBus", "Guard"]

QUEUE_SIZE = 1000
REPLAY_BATCH = 500

type _Key = tuple[str, str]  # (user_id, session_id): isolation per user holds here too
type _Publication = asyncio.Task[SessionEvent | None]


class EventBus:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        queue_size: int = QUEUE_SIZE,
        replay_batch: int = REPLAY_BATCH,
    ) -> None:
        self._factory = session_factory
        self._writer = EventWriter(session_factory)
        self._queue_size = queue_size
        self._replay_batch = replay_batch
        self._states: dict[_Key, SessionState] = {}
        self._inflight: dict[_Key, set[_Publication]] = {}

    # --- Publication ---------------------------------------------------------------------

    async def publish(
        self,
        *,
        user_id: str,
        session_id: str,
        type: EventType,
        payload: BaseModel | dict[str, Any],
        agent: str | None = None,
    ) -> SessionEvent:
        """Writes then broadcasts; `ValueError` if the payload does not follow the catalogue,
        `AppError("session_not_found")` if the session does not belong to `user_id`.

        The write and the broadcast form a protected task: cancelling the caller (session
        cancelled mid-publication) never leaves an event written but not broadcast.
        """
        event = await self._protected(user_id, session_id, type, payload, agent, None)
        if event is None:  # impossible: without a guard, nothing refuses the write
            raise RuntimeError("publication without guard refused")
        return event

    async def publish_with(
        self,
        *,
        user_id: str,
        session_id: str,
        type: EventType,
        payload: BaseModel | dict[str, Any],
        guard: Guard,
        agent: str | None = None,
    ) -> SessionEvent | None:
        """Like `publish`, with `guard(db)` called inside the event's transaction (under the
        session lock): `False` -> nothing is written or broadcast, `None`; `True` -> guard
        and event committed together, then broadcast. If the insert fails, the guard is
        rolled back with it (D52 §2, D61)."""
        return await self._protected(user_id, session_id, type, payload, agent, guard)

    async def _protected(
        self,
        user_id: str,
        session_id: str,
        type: EventType,
        payload: BaseModel | dict[str, Any],
        agent: str | None,
        guard: Guard | None,
    ) -> SessionEvent | None:
        data = validate_payload(type, payload).model_dump(mode="json")
        key = (user_id, session_id)
        task = asyncio.ensure_future(self._publish(key, type, data, agent, guard))
        tasks = self._inflight.setdefault(key, set())
        tasks.add(task)
        task.add_done_callback(lambda done: self._landed(key, done))
        return await asyncio.shield(task)

    def _landed(self, key: _Key, task: _Publication) -> None:
        tasks = self._inflight.get(key)
        if tasks is not None:
            tasks.discard(task)
            if not tasks:
                del self._inflight[key]

    async def _publish(
        self, key: _Key, type: str, data: dict[str, Any], agent: str | None, guard: Guard | None
    ) -> SessionEvent | None:
        user_id, session_id = key
        while True:
            state = self._state(key)
            state.publishers += 1
            try:
                async with state.lock:
                    if state.closed:
                        continue  # `close` removed this state while we waited for the lock
                    row = await self._writer.write(
                        state, user_id, session_id, type, data, agent, guard
                    )
                    if row is None:
                        return None  # guard refused: nothing written, nothing to broadcast
                    event = to_event(row)
                    for sub in state.subscribers:
                        sub.offer(event)
                    return event
            finally:
                state.publishers -= 1
                self._release(key, state)

    # --- Subscription --------------------------------------------------------------------

    async def subscribe(
        self, *, user_id: str, session_id: str, after_seq: int = 0
    ) -> AsyncGenerator[SessionEvent, None]:
        """Replay of the events `seq > after_seq` then live, with no gap or duplicate.

        Ends after `close` of the session; to be closed by `aclose` (or `aclosing`).
        """
        key = (user_id, session_id)
        state = self._state(key)
        sub = Subscriber(asyncio.Queue(self._queue_size))
        state.subscribers.add(sub)  # 1. register the queue before any database read
        last = after_seq
        try:
            while True:
                # Before re-reading: the queue receives again, nothing falls between the two.
                sub.overflowed = False
                while True:  # 2. replay in batches
                    batch = await self._read_after(user_id, session_id, last)
                    for event in batch:
                        yield event
                        last = event.seq
                    if len(batch) < self._replay_batch:
                        break
                gap = False
                while (live := await sub.next_live()) is not None:  # 3. live
                    if live.seq <= last:
                        continue  # already emitted (replay)
                    if live.seq > last + 1:
                        gap = True  # writer outside the bus: the database has what is missing
                        break
                    yield live
                    last = live.seq
                if not (gap or sub.overflowed):
                    return  # session closed
        finally:  # 4. unregister
            state.subscribers.discard(sub)
            self._release(key, state)

    async def _read_after(
        self, user_id: str, session_id: str, after_seq: int
    ) -> list[SessionEvent]:
        async with self._factory() as db:
            rows = await EventRepository(db, user_id).list_after(
                session_id, after_seq, limit=self._replay_batch
            )
        return [to_event(row) for row in rows]

    # --- End of session and in-memory state ----------------------------------------------

    async def close(self, *, user_id: str, session_id: str) -> None:
        """End of session (terminal status): the subscribers receive what is queued then
        stop; the in-memory state (lock, cache, subscribers) is released. A later `publish`
        starts again from the database."""
        key = (user_id, session_id)
        state = self._states.get(key)
        if state is None:
            return
        async with state.lock:  # waits for the publication in progress
            state.closed = True
            if self._states.get(key) is state:
                del self._states[key]
            for sub in state.subscribers:
                sub.close()

    async def flush(self, *, user_id: str | None = None, session_id: str | None = None) -> None:
        """Waits for the publications already started (protected: their caller may have been
        cancelled, they go on without it): all of them, or only those of the session `(user_id,
        session_id)` (N5). After a task stops (pause, cancellation), everything it was
        publishing is written: the `last_seq` read afterwards counts it (D56)."""
        if (user_id is None) != (session_id is None):
            raise ValueError("flush: user_id and session_id go together")
        if user_id is None or session_id is None:
            pending = [task for tasks in self._inflight.values() for task in tasks]
        else:
            pending = list(self._inflight.get((user_id, session_id), ()))
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

    async def aclose(self) -> None:
        """Server shutdown, before the engine closes: waits for the protected writes still in
        flight, until none is left."""
        while self._inflight:
            await self.flush()

    def subscriber_count(self, *, user_id: str, session_id: str) -> int:
        state = self._states.get((user_id, session_id))
        return len(state.subscribers) if state is not None else 0

    def queued(self, *, user_id: str, session_id: str) -> int:
        """Events waiting in the subscribers' queues (bounded by `queue_size`)."""
        state = self._states.get((user_id, session_id))
        return sum(s.queue.qsize() for s in state.subscribers) if state is not None else 0

    def tracked_sessions(self) -> int:
        return len(self._states)

    def _state(self, key: _Key) -> SessionState:
        state = self._states.get(key)
        if state is None:
            state = self._states[key] = SessionState()
        return state

    def _release(self, key: _Key, state: SessionState) -> None:
        """Forgets a state that became useless: no subscriber, no publication, no cached `seq` (a
        session never published here, or belonging to another user). The cache itself lives until
        `close`, so as not to read `max_seq` again on each event of a session with no subscriber."""
        if state.subscribers or state.publishers or state.last_seq is not None:
            return
        state.closed = True
        if self._states.get(key) is state:
            del self._states[key]
