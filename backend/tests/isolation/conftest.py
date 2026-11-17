"""Fixtures de l'isolation : l'application en vrai mode Google (cookies de session réels), dont le
point `token` de Google est `FakeGoogle` (`httpx.MockTransport`) : aucun réseau. Chaque navigateur
a ses propres cookies ; `act_as` sert, lui, aux routeurs en mode local."""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AsyncExitStack

import httpx
import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from app.config import Settings
from app.core.providers import MemoryProviders, PublishingProviders, ResearchProviders
from app.main import create_app
from tests.features.auth.support import FakeGoogle, sign_in

Browser = Callable[[str], Awaitable[httpx.AsyncClient]]


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
    app = create_app(
        google_settings,
        memory_providers=memory_providers,
        research_providers=research_providers,
        publishing_providers=publishing_providers,
    )
    async with LifespanManager(app), google.plug_into(app):
        yield app


@pytest.fixture
async def google_client_factory(google_app: FastAPI, google: FakeGoogle) -> AsyncIterator[Browser]:
    """`await browser(email)` : un nouveau navigateur (cookies à lui) connecté par le faux
    fournisseur sous cette adresse. Fermés à la fin du test."""
    async with AsyncExitStack() as stack:

        async def browser(email: str) -> httpx.AsyncClient:
            transport = httpx.ASGITransport(app=google_app, raise_app_exceptions=False)
            client = await stack.enter_async_context(
                httpx.AsyncClient(transport=transport, base_url="http://test")
            )
            back = await sign_in(client, google, email)
            assert back.status_code == 302 and back.headers["location"].endswith("/"), back.headers
            return client

        yield browser
