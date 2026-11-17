"""Un compte en mode Google : l'application et son client, connectés comme l'utilisatrice que le
test choisit (`act_as`)."""

from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx
import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from sqlalchemy import Column, String, Table
from sqlalchemy.ext.asyncio import AsyncEngine

from app.config import Settings
from app.core.providers import MemoryProviders, PublishingProviders, ResearchProviders
from app.db.base import Base
from app.main import create_app


@dataclass
class GoogleApp:
    app: FastAPI
    client: httpx.AsyncClient


@pytest.fixture
async def google_app(
    settings: Settings,
    db_engine: AsyncEngine,
    memory_providers: MemoryProviders,
    research_providers: ResearchProviders,
    publishing_providers: PublishingProviders,
) -> AsyncIterator[GoogleApp]:
    google = settings.model_copy(
        update={
            "auth_mode": "google",
            "google_client_id": "client-de-test.example.invalid",
            "google_client_secret": "secret-de-test",
        }
    )
    app = create_app(
        google,
        memory_providers=memory_providers,
        research_providers=research_providers,
        publishing_providers=publishing_providers,
    )
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield GoogleApp(app, client)


@pytest.fixture
async def extra_table(db_engine: AsyncEngine) -> AsyncIterator[Table]:
    """Une table ajoutée demain : une colonne `user_id`, rien d'autre à déclarer."""
    table = Table(
        "future_things",
        Base.metadata,
        Column("id", String(36), primary_key=True),
        Column("user_id", String(36)),
        Column("label", String(40)),
    )
    async with db_engine.begin() as conn:
        await conn.run_sync(table.create)
    yield table
    async with db_engine.begin() as conn:
        await conn.run_sync(table.drop)
    Base.metadata.remove(table)
