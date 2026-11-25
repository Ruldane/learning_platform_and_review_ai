"""Memory in the application's lifecycle: what requests and the worker share. Opened
by the lifespan (`app.state.memory`), before the agent engine."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.providers import MemoryProviders
from app.features.memory.service.indexer import MemoryIndexer

if TYPE_CHECKING:
    # `jobs` imports the ingestion chain, which imports this module: deferred import.
    from app.features.memory.service.jobs import MemoryJobs


@dataclass(frozen=True)
class MemoryRuntime:
    session_factory: async_sessionmaker[AsyncSession]
    providers: MemoryProviders
    indexer: MemoryIndexer
    jobs: "MemoryJobs"
    _learn_locks: dict[str, asyncio.Lock] = field(default_factory=dict, repr=False, compare=False)

    def learn_lock(self, user_id: str) -> asyncio.Lock:
        """The user's "Already learned" lock (D71): covers only the "session already open?
        otherwise start" section, so a double click starts only one session. Local to this
        process (single worker). One lock per user, kept for the process lifetime."""
        return self._learn_locks.setdefault(user_id, asyncio.Lock())


@asynccontextmanager
async def memory_runtime(
    session_factory: async_sessionmaker[AsyncSession], providers: MemoryProviders
) -> AsyncIterator[MemoryRuntime]:
    """Starts the worker (including resuming `queued` and `processing` documents) and stops it
    on exit: an interrupted import stays `processing` and restarts on the next startup."""
    from app.features.memory.service.jobs import MemoryJobs

    built: list[MemoryRuntime] = []
    jobs = MemoryJobs(lambda: built[0])
    runtime = MemoryRuntime(session_factory, providers, MemoryIndexer(providers.index), jobs)
    built.append(runtime)
    await jobs.start()
    try:
        yield runtime
    finally:
        await jobs.aclose()
