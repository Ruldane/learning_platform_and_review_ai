"""Learning in the application's lifetime: what HTTP requests and agents share (database,
session launcher, per-goal locks). Opened by the lifespan (`app.state.learning`), before the
agent engine (D87)."""

import asyncio
import weakref
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.launcher import SessionLauncher


@dataclass
class LearningRuntime:
    session_factory: async_sessionmaker[AsyncSession]
    launcher: SessionLauncher
    # Weak: a lock nobody holds anymore disappears (otherwise one entry per goal).
    _goal_locks: weakref.WeakValueDictionary[tuple[str, str], asyncio.Lock] = field(
        default_factory=weakref.WeakValueDictionary, repr=False, compare=False
    )

    def _lock(self, user_id: str, goal_id: str) -> asyncio.Lock:
        key = (user_id, goal_id)
        lock = self._goal_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._goal_locks[key] = lock
        return lock

    @asynccontextmanager
    async def goal_lock(self, user_id: str, goal_id: str) -> AsyncIterator[None]:
        """A goal's critical section: path choice (`choose` route), saved choice and program
        start (port, `finalize` node). Double click, or a choice at the same time as a generic
        resume: a single `program_builder`. Local to this process (a single worker, like the
        research locks)."""
        async with self._lock(user_id, goal_id):
            yield
