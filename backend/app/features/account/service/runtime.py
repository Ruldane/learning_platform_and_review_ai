"""Ce que « Mes données » reçoit du démarrage : le stockage des fichiers, le moteur d'agents (que
« Tout supprimer » interroge pour annuler les sessions en cours et effacer leurs points de
reprise), la fabrique de sessions de base (sa transaction) et les verrous par compte."""

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
