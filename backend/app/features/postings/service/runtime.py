"""Postings in the application's life (D122): what the `postings` and `gap` routes and the
Analyst's port (`AgentGapStore`) share: database, web search (reading the link), memory (`offre`
item, "possible" duplicates), session launcher (bound to the engine later) and locks. Created by
the lifespan before the agent engine (`app.state.career.postings`)."""

import asyncio
import weakref
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.features.lessons.service.runtime import Launcher
from app.features.memory.service.runtime import MemoryRuntime
from app.features.research.service.runtime import ResearchRuntime

GRAPH = "gap_analysis"
SUBJECT = "posting"


def utc_now() -> datetime:
    return datetime.now(UTC)


class KeyLocks:
    """Per-key locks, weak (a lock nobody holds anymore disappears). Specific to this process (a
    single worker, like the application's other locks)."""

    def __init__(self) -> None:
        self._locks: weakref.WeakValueDictionary[tuple[str, str], asyncio.Lock] = (
            weakref.WeakValueDictionary()
        )

    def get(self, user_id: str, key: str) -> asyncio.Lock:
        lock = self._locks.get((user_id, key))
        if lock is None:
            lock = asyncio.Lock()
            self._locks[(user_id, key)] = lock
        return lock


def company_lock(locks: KeyLocks, user_id: str, key: str) -> asyncio.Lock:
    """The lock on the company record `key` (`company_key`): the CV review and the kit file both
    create it; `locks` is the same `KeyLocks` on both sides (`bootstrap_career`)."""
    return locks.get(user_id, f"company:{key}")


@dataclass
class PostingsRuntime:
    session_factory: async_sessionmaker[AsyncSession]
    research: ResearchRuntime
    memory: MemoryRuntime
    launcher: Launcher
    now: Callable[[], datetime] = utc_now
    # Adding a posting: one lock per normalized link or text fingerprint (two submissions
    # of the same link wait for each other; the unique index remains the last safeguard).
    source_locks: KeyLocks = field(default_factory=KeyLocks, repr=False, compare=False)
    # Starting the analysis: one lock per posting (adding and re-running start only one).
    launch_locks: KeyLocks = field(default_factory=KeyLocks, repr=False, compare=False)
