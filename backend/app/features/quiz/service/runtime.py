"""Quizzes in the application's life (D101): what the routes and the Examiner's port
(`AgentQuizStore`) share: database, session launcher, program (lock, follow-up tasks), memory
(level reflection), clock and per-quiz locks. Created by the lifespan before the agent engine
(`app.state.quiz`), with the launcher still unbound."""

import asyncio
import weakref
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.clock import local_today, user_zone
from app.features.lessons.service.runtime import Launcher
from app.features.memory.service.runtime import MemoryRuntime
from app.features.program.service.runtime import ProgramRuntime
from app.features.settings.service import SettingsService

GRAPH = "quiz"
SUBJECT = "quiz"


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class QuizRuntime:
    session_factory: async_sessionmaker[AsyncSession]
    launcher: Launcher
    program: ProgramRuntime
    memory: MemoryRuntime
    now: Callable[[], datetime] = utc_now  # replaced by the tests (time frozen)
    # Weak: a lock nobody holds anymore disappears.
    _locks: weakref.WeakValueDictionary[tuple[str, str], asyncio.Lock] = field(
        default_factory=weakref.WeakValueDictionary, repr=False, compare=False
    )

    @asynccontextmanager
    async def quiz_lock(self, user_id: str, key: str) -> AsyncIterator[None]:
        """Launch of a quiz (key: the module) or of an attempt (key: the quiz): two simultaneous
        submissions go one after the other. Specific to this process (a single worker); the unique
        index `uq_quiz_attempts_grading` remains the last safeguard (F3)."""
        lock = self._locks.get((user_id, key))
        if lock is None:
            lock = asyncio.Lock()
            self._locks[(user_id, key)] = lock
        async with lock:
            yield

    async def today(self, db: AsyncSession, user_id: str) -> date:
        """January's day in their time zone (D98)."""
        zone = user_zone((await SettingsService(db, user_id).get()).timezone)
        return local_today(zone, self.now())
