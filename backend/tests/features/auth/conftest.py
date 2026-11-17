from collections.abc import AsyncIterator, Awaitable, Callable

import httpx
import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.config import Settings
from app.core.providers import MemoryProviders, PublishingProviders, ResearchProviders
from app.db.models.accounts import AuthSession, User
from app.main import create_app
from tests.features.auth.support import FakeGoogle


@pytest.fixture
def google(google_settings: Settings) -> FakeGoogle:
    return FakeGoogle(google_settings)


@pytest.fixture
async def google_app(
    google_settings: Settings,
    google: FakeGoogle,
    db_engine: AsyncEngine,
    memory_providers: MemoryProviders,
    research_providers: ResearchProviders,
    publishing_providers: PublishingProviders,
) -> AsyncIterator[FastAPI]:
    """L'application en mode Google, dont le point `token` de Google est `FakeGoogle`."""
    app = create_app(
        google_settings,
        memory_providers=memory_providers,
        research_providers=research_providers,
        publishing_providers=publishing_providers,
    )
    async with LifespanManager(app), google.plug_into(app):
        yield app


@pytest.fixture
async def google_client(google_app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=google_app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def count_users(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> Callable[[], Awaitable[int]]:
    async def count() -> int:
        async with db_session_factory() as db:
            return (await db.execute(select(func.count()).select_from(User))).scalar_one()

    return count


@pytest.fixture
async def count_sessions(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> Callable[[], Awaitable[int]]:
    async def count() -> int:
        async with db_session_factory() as db:
            return (await db.execute(select(func.count()).select_from(AuthSession))).scalar_one()

    return count
