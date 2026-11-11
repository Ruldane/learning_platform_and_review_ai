"""La mémoire dans la vie de l'application : ce que les requêtes (et, plus loin, le worker)
partagent. Ouvert par le lifespan (`app.state.memory`), avant le moteur d'agents."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.providers import MemoryProviders
from app.features.memory.service.indexer import MemoryIndexer


@dataclass(frozen=True)
class MemoryRuntime:
    session_factory: async_sessionmaker[AsyncSession]
    providers: MemoryProviders
    indexer: MemoryIndexer


@asynccontextmanager
async def memory_runtime(
    session_factory: async_sessionmaker[AsyncSession], providers: MemoryProviders
) -> AsyncIterator[MemoryRuntime]:
    yield MemoryRuntime(session_factory, providers, MemoryIndexer(providers.index))
