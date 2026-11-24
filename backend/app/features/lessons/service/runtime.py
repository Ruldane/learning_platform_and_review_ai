"""Lessons in the application's lifetime (D91): what chained production, the Writer's port
(`AgentLessonStore`), the scheduled job and the routes share (database, session launcher, memory,
research, file storage, PDF rendering, per-program locks). Created by the lifespan before the
agent engine (`app.state.lessons`), with the launcher not bound yet."""

import asyncio
import weakref
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.creation import PrepareSession
from app.core.providers import PublishingProviders
from app.features.memory.service.runtime import MemoryRuntime
from app.features.research.service.runtime import ResearchRuntime
from app.providers.storage.base import FileStorage


class Launcher(Protocol):
    """What production expects from the session launcher (`SessionLauncher`, D82)."""

    async def start(
        self,
        user_id: str,
        graph: str,
        input: dict[str, Any],
        *,
        subject_type: str | None = None,
        subject_id: str | None = None,
        prepare: PrepareSession | None = None,
    ) -> str: ...


class ProgramLocks:
    """Lessons locks, one per program: production (validation, scheduled job, end of a lesson)
    runs under them. Weak: a lock nobody holds anymore disappears. Local to this process (a
    single worker, like the program and research locks)."""

    def __init__(self) -> None:
        self._locks: weakref.WeakValueDictionary[tuple[str, str], asyncio.Lock] = (
            weakref.WeakValueDictionary()
        )

    def get(self, user_id: str, program_id: str) -> asyncio.Lock:
        key = (user_id, program_id)
        lock = self._locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[key] = lock
        return lock


@dataclass
class LessonsRuntime:
    session_factory: async_sessionmaker[AsyncSession]
    launcher: Launcher
    memory: MemoryRuntime
    research: ResearchRuntime
    storage: FileStorage
    publishing: PublishingProviders
    _locks: ProgramLocks = field(default_factory=ProgramLocks, repr=False, compare=False)

    @asynccontextmanager
    async def lessons_lock(self, user_id: str, program_id: str) -> AsyncIterator[None]:
        async with self._locks.get(user_id, program_id):
            yield
