"""What "My data" receives from startup: file storage, the agent engine (which "Delete
everything" queries to cancel running sessions and erase their checkpoints), the database
session factory (its transaction) and the per-account locks."""

from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.handle import AgentRuntime
from app.features.memory.service.indexer import MemoryIndexer
from app.features.postings.service.runtime import KeyLocks
from app.providers.storage.base import FileStorage
from app.providers.vector.base import MemoryRepository


@dataclass(frozen=True)
class AccountRuntime:
    session_factory: async_sessionmaker[AsyncSession]
    storage: FileStorage
    index: MemoryRepository
    indexer: MemoryIndexer
    runtime: AgentRuntime
    locks: KeyLocks = field(default_factory=KeyLocks, repr=False, compare=False)
