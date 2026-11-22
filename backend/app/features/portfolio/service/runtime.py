from collections.abc import Callable
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import Cipher
from app.features.postings.service.runtime import KeyLocks
from app.providers.storage.base import FileStorage


@dataclass
class PortfolioRuntime:
    factory: async_sessionmaker[AsyncSession]
    storage: FileStorage
    cipher: Cipher
    origin: Callable[[], str | None]
    locks: KeyLocks = field(default_factory=KeyLocks, repr=False)
