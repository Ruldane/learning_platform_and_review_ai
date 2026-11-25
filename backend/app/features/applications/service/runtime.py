"""Applications in the life of the application (D139): database, session launcher (linked to
the engine later, for the tracking Assistant, 7.4) and locks. Created by the lifespan
(`app.state.career.applications`)."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.portfolio_urls import no_origin
from app.features.lessons.service.runtime import Launcher
from app.features.postings.service.runtime import KeyLocks, utc_now

LOCK_KEY = "applications"


@dataclass
class ApplicationsRuntime:
    session_factory: async_sessionmaker[AsyncSession]
    launcher: Launcher
    now: Callable[[], datetime] = utc_now
    # Creation, events and version adoption: one lock per user (the duplicate check
    # and the write of the record never overlap).
    locks: KeyLocks = field(default_factory=KeyLocks, repr=False, compare=False)
    # Company record creation: the same `KeyLocks` as the CV reviews (M7).
    company_locks: KeyLocks = field(default_factory=KeyLocks, repr=False, compare=False)
    portfolio_origin: Callable[[], str | None] = no_origin

    def lock(self, user_id: str) -> asyncio.Lock:
        """The applications lock of the user."""
        return self.locks.get(user_id, LOCK_KEY)
