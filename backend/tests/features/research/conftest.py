from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.providers import ResearchProviders
from app.core.security import Cipher
from app.db.models.accounts import User
from app.db.models.research import SearchUsage
from app.features.research.repository import month_total
from app.features.research.service.cache import WebCache
from app.features.research.service.runtime import ResearchRuntime
from app.features.research.service.usage import key_fingerprint
from app.features.settings.keys_service import DbKeyReader
from app.features.settings.schemas import UserSettings
from app.features.settings.service import SettingsService
from app.providers.search.base import SearchProvider, SearchResult
from app.providers.search.fake import FakeSearch
from tests.support.memory import FakeWebReader


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


# --- Service de recherche (3.6) : faux SearXNG, faux Brave, faux lecteur web, clé `.env` réglable.

UID = "u1"
OTHER = "u2"
BRAVE_KEY = "BSA-test-key-0001"


def hit(url: str, title: str = "Titre") -> SearchResult:
    return SearchResult(title=title, url=url, snippet="extrait", engine="fake", published=None)


@dataclass
class BraveFactory:
    """Fabrique Brave qui note chaque clé reçue : « Brave construit » = une entrée."""

    search: FakeSearch
    keys: list[str] = field(default_factory=list)

    def __call__(self, api_key: str) -> SearchProvider:
        self.keys.append(api_key)
        return self.search


@pytest.fixture
def searxng_fake() -> FakeSearch:
    return FakeSearch("searxng")


@pytest.fixture
def brave_fake() -> FakeSearch:
    return FakeSearch("brave")


@pytest.fixture
def brave_factory(brave_fake: FakeSearch) -> BraveFactory:
    return BraveFactory(brave_fake)


@pytest.fixture
def fake_web() -> FakeWebReader:
    return FakeWebReader()


@pytest.fixture
def env_keys() -> dict[str, str | None]:
    return {}


@pytest.fixture
async def users(db_session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with db_session_factory() as session:
        session.add(User(id=UID, user_id=UID, name="Jane Doé", email="jane@x.fr"))
        session.add(User(id=OTHER, user_id=OTHER, name="Bob Martin", email="bob@y.fr"))
        await session.commit()


@pytest.fixture
def runtime(
    users: None,
    db_session_factory: async_sessionmaker[AsyncSession],
    searxng_fake: FakeSearch,
    brave_factory: BraveFactory,
    fake_web: FakeWebReader,
    env_keys: dict[str, str | None],
    clock: Clock,
) -> ResearchRuntime:
    providers = ResearchProviders(searxng=searxng_fake, brave=brave_factory, web=fake_web)
    keys = DbKeyReader(db_session_factory, Cipher(Fernet.generate_key()), env_keys)
    return ResearchRuntime(db_session_factory, providers, keys, now=clock)


@pytest.fixture
def runtime_with_brave_key(
    runtime: ResearchRuntime, env_keys: dict[str, str | None]
) -> ResearchRuntime:
    env_keys["brave"] = BRAVE_KEY
    return runtime


async def set_settings(
    factory: async_sessionmaker[AsyncSession], user_id: str, **fields: Any
) -> None:
    async with factory() as session:
        service = SettingsService(session, user_id)
        current = await service.get()
        await service.replace(UserSettings.model_validate(current.model_dump() | fields))
        await session.commit()


async def seed_brave_usage(
    factory: async_sessionmaker[AsyncSession],
    count: int,
    *,
    user_id: str = UID,
    month: str = "2026-11",
    api_key: str = BRAVE_KEY,
) -> None:
    async with factory() as session:
        session.add(
            SearchUsage(
                user_id=user_id,
                provider="brave",
                month=month,
                key_fingerprint=key_fingerprint(api_key),
                count=count,
            )
        )
        await session.commit()


async def brave_total(
    factory: async_sessionmaker[AsyncSession], month: str = "2026-11", api_key: str = BRAVE_KEY
) -> int:
    async with factory() as session:
        return await month_total(
            session, provider="brave", month=month, fingerprint=key_fingerprint(api_key)
        )
