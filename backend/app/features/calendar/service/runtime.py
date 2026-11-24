from asyncio import Lock
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from weakref import WeakValueDictionary

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import AppError
from app.core.security import Cipher
from app.db.base import utcnow
from app.providers.calendar.base import CalendarPort


@dataclass
class CalendarRuntime:
    factory: async_sessionmaker[AsyncSession]
    cipher: Cipher
    port: CalendarPort | None
    secure: bool = False
    now: Callable[[], datetime] = utcnow
    _locks: WeakValueDictionary[str, Lock] = field(default_factory=WeakValueDictionary)

    def provider(self) -> CalendarPort:
        if self.port is None:
            raise AppError("calendar_not_configured", "Google Calendar is not configured.", 409)
        return self.port

    def lock(self, user_id: str) -> Lock:
        lock = self._locks.get(user_id)
        if lock is None:
            lock = self._locks[user_id] = Lock()
        return lock
