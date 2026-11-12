from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.features.research.service.cache import WebCache


class Clock:
    """Horloge réglable : `WebCache` la lit au lieu de `utcnow`."""

    def __init__(self) -> None:
        self.current = datetime(2026, 11, 12, 9, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.current

    def advance(self, **delta: float) -> None:
        self.current += timedelta(**delta)


@pytest.fixture
async def db(db_session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    async with db_session_factory() as session:
        yield session


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def cache(db: AsyncSession, clock: Clock) -> WebCache:
    return WebCache(db, "u1", now=clock)
