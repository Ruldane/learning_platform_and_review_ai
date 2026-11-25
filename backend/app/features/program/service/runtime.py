"""The program in the application's life: what the HTTP requests and the Strategist's port share
(database, memory for the level reflection, lesson production launched by validation,
per-program locks). Opened by the lifespan (`app.state.program`), before the agent engine
(D88, D91)."""

import asyncio
import weakref
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.features.lessons.service.production import ProductionContext
from app.features.memory.service.runtime import MemoryRuntime


@dataclass
class ProgramRuntime:
    session_factory: async_sessionmaker[AsyncSession]
    memory: MemoryRuntime
    # Producing lessons (D91): validation starts weeks 1 and 2; `None` outside
    # the application (tests of the program alone).
    lessons: ProductionContext | None = None
    # Validations requested by the route and resumed in the Strategist's session: a second
    # click while `finalize` runs returns the same state (202) instead of a 409.
    validating: set[str] = field(default_factory=set, repr=False, compare=False)
    # Weak: a lock nobody holds anymore disappears (one entry per program otherwise).
    _locks: weakref.WeakValueDictionary[tuple[str, str], asyncio.Lock] = field(
        default_factory=weakref.WeakValueDictionary, repr=False, compare=False
    )

    def _lock(self, user_id: str, program_id: str) -> asyncio.Lock:
        key = (user_id, program_id)
        lock = self._locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[key] = lock
        return lock

    @asynccontextmanager
    async def program_lock(self, user_id: str, program_id: str) -> AsyncIterator[None]:
        """Critical section of a program: any change by January (move, addition, deletion, start
        date), the validation and the writing of a version by the Strategist. The rules (85%,
        practice, quiz) are checked under this lock, on the re-read state: two simultaneous moves
        never exceed the cap together. Specific to this process (a single worker, like the learning
        and search locks)."""
        async with self._lock(user_id, program_id):
            yield
