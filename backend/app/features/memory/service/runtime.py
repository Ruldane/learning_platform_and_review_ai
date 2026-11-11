"""La mémoire dans la vie de l'application : ce que les requêtes et le worker partagent. Ouvert
par le lifespan (`app.state.memory`), avant le moteur d'agents."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.providers import MemoryProviders
from app.features.memory.service.indexer import MemoryIndexer

if TYPE_CHECKING:
    # `jobs` importe la chaîne d'ingestion, qui importe ce module : import différé.
    from app.features.memory.service.jobs import MemoryJobs


@dataclass(frozen=True)
class MemoryRuntime:
    session_factory: async_sessionmaker[AsyncSession]
    providers: MemoryProviders
    indexer: MemoryIndexer
    jobs: "MemoryJobs"


@asynccontextmanager
async def memory_runtime(
    session_factory: async_sessionmaker[AsyncSession], providers: MemoryProviders
) -> AsyncIterator[MemoryRuntime]:
    """Démarre le worker (reprise des documents `queued` et `processing` comprise) et l'arrête à
    la sortie : un import interrompu reste `processing` et repart au prochain démarrage."""
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
