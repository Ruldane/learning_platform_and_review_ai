"""Web search in the application's life: what the HTTP requests and the agents share (providers,
key reader, locks). Opened by the lifespan (`app.state.research`)."""

import asyncio
import weakref
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.providers import ResearchProviders
from app.db.base import utcnow
from app.features.research.repository import WebCacheRepository
from app.features.research.service.pacing import BRAVE_INTERVAL_S, KeyPacer
from app.providers.llm.base import KeyReader

# Purge of expired entries from a user's web cache: at most once an hour, on
# the occasion of a write to their cache (D76).
PURGE_EVERY = timedelta(hours=1)


@dataclass
class ResearchRuntime:
    session_factory: async_sessionmaker[AsyncSession]
    providers: ResearchProviders
    keys: KeyReader
    now: Callable[[], datetime] = utcnow
    # One lock for the process: the monthly counter of a Brave key is shared.
    brave_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    # Brave pacing per key (1 request per second on the free tier), for the whole process.
    brave_pacer: KeyPacer = field(default_factory=lambda: KeyPacer(BRAVE_INTERVAL_S))
    # Weak: a lock nobody holds anymore disappears (one entry per session otherwise).
    _session_locks: weakref.WeakValueDictionary[tuple[str, str], asyncio.Lock] = field(
        default_factory=weakref.WeakValueDictionary, repr=False, compare=False
    )
    _last_purge: dict[str, datetime] = field(default_factory=dict, repr=False, compare=False)

    def session_lock(self, user_id: str, session_id: str) -> asyncio.Lock:
        """Lock of a search session: the check "already done? limit reached?", the provider call and
        the write form a single section, so that two simultaneous calls (replayed node) count only
        once. Specific to this process (a single worker)."""
        key = (user_id, session_id)
        lock = self._session_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._session_locks[key] = lock
        return lock

    def purge_due(self, user_id: str, now: datetime) -> bool:
        """True (and noted) if the user's cache has not been purged since `PURGE_EVERY`."""
        last = self._last_purge.get(user_id)
        if last is not None and now - last < PURGE_EVERY:
            return False
        self._last_purge[user_id] = now
        return True

    async def purge_if_due(self, db: AsyncSession, user_id: str) -> None:
        """Deletes the expired entries of the user's cache, at most once per `PURGE_EVERY`, within
        the caller's write transaction (D76)."""
        now = self.now()
        if self.purge_due(user_id, now):
            await WebCacheRepository(db, user_id).purge_expired(now)
