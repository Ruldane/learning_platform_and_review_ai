"""Replanning in the application's lifetime (D106): what the routes, the Strategist port
(`AgentReplanStore`) and the scheduled review share: database, session launcher (bound to the
engine afterwards), program (lock, version writes), clock and launch locks.
Created by the lifespan before the agent engine (`app.state.replan`)."""

import asyncio
import weakref
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.clock import local_today, user_zone
from app.features.calendar.service.runtime import CalendarRuntime
from app.features.lessons.service.runtime import Launcher
from app.features.program.service.runtime import ProgramRuntime
from app.features.settings.service import SettingsService

GRAPH = "replan"
SUBJECT = "program"


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class ReplanRuntime:
    session_factory: async_sessionmaker[AsyncSession]
    launcher: Launcher
    program: ProgramRuntime
    now: Callable[[], datetime] = utc_now  # replaced by tests (frozen time)
    calendar: CalendarRuntime | None = field(default=None, kw_only=True)
    # Weak: a lock that nobody holds any more disappears.
    _locks: weakref.WeakValueDictionary[tuple[str, str], asyncio.Lock] = field(
        default_factory=weakref.WeakValueDictionary, repr=False, compare=False
    )

    @asynccontextmanager
    async def launch_lock(self, user_id: str, program_id: str) -> AsyncIterator[None]:
        """Launching a replanning: two simultaneous requests on a program go one after the other
        (the second sees the first one's session: 409 `replan_open`).
        Local to this process (a single worker)."""
        lock = self._locks.get((user_id, program_id))
        if lock is None:
            lock = asyncio.Lock()
            self._locks[(user_id, program_id)] = lock
        async with lock:
            yield

    async def zone(self, db: AsyncSession, user_id: str) -> ZoneInfo:
        return user_zone((await SettingsService(db, user_id).get()).timezone)

    async def today(self, db: AsyncSession, user_id: str) -> date:
        """January's day in her time zone (D98)."""
        return local_today(await self.zone(db, user_id), self.now())
