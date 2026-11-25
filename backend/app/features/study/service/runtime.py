"""Guided study in the application's life (D103): what the routes and the Tutor's port
(`AgentStudyStore`) share: database, session launcher, program (lock, ticked tasks), memory
(level reflection), clock and lock per user. Created by the lifespan before the agent engine
(`app.state.study`), with the launcher still unbound."""

import asyncio
import weakref
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.clock import local_today, user_zone
from app.features.lessons.service.runtime import Launcher
from app.features.memory.service.runtime import MemoryRuntime
from app.features.program.service.runtime import ProgramRuntime
from app.features.settings.service import SettingsService

GRAPH = "study_session"
SUBJECT = "study_session"  # subject of the agent session: the study session (D103)


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class StudyRuntime:
    session_factory: async_sessionmaker[AsyncSession]
    launcher: Launcher
    program: ProgramRuntime
    memory: MemoryRuntime
    now: Callable[[], datetime] = utc_now  # replaced by the tests (time frozen)
    _locks: weakref.WeakValueDictionary[str, asyncio.Lock] = field(
        default_factory=weakref.WeakValueDictionary, repr=False, compare=False
    )

    @asynccontextmanager
    async def study_lock(self, user_id: str) -> AsyncIterator[None]:
        """Start, end and abandonment of a user's session go one after the other. Taken BEFORE the
        program lock (never the reverse). Specific to this process (a single worker); the unique
        index `uq_study_sessions_open` remains the last safeguard."""
        lock = self._locks.get(user_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[user_id] = lock
        async with lock:
            yield

    async def zone(self, db: AsyncSession, user_id: str) -> ZoneInfo:
        return user_zone((await SettingsService(db, user_id).get()).timezone)

    async def today(self, db: AsyncSession, user_id: str) -> date:
        """January's day in their time zone (D98)."""
        return local_today(await self.zone(db, user_id), self.now())
