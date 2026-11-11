from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

import app.db.models  # noqa: F401  (enregistre les modèles sur Base.metadata)
from app.config import Settings
from app.core.providers import MemoryProviders
from app.db.base import Base
from app.db.engine import create_engine, create_session_factory
from app.main import create_app
from tests.support.memory import fake_memory_providers


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    # Isolé du .env et de l'environnement du développeur : tests déterministes.
    return Settings(_env_file=None, data_dir=tmp_path, cors_origin="http://localhost:5173")


# Base de test : un vrai fichier SQLite `tmp_path/app.db` (celui de `settings.database_url`).
# `db_engine` y crée le schéma avant le démarrage de l'app ; le lifespan de l'app ouvre son
# propre moteur sur le même fichier. `client` et `db_session` voient donc les mêmes données,
# à condition que `db_session` ait commité (un `flush` suffit pour les tests de repository).
@pytest.fixture
async def db_engine(settings: Settings) -> AsyncIterator[AsyncEngine]:
    engine = create_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
def db_session_factory(db_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return create_session_factory(db_engine)


@pytest.fixture
async def db_session(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with db_session_factory() as session:
        yield session


# Mémoire : l'embedder déterministe et Qdrant en mémoire remplacent Ollama et Qdrant dans toute la
# suite. `app` et `client_google_mode` les injectent : aucun test ne peut atteindre un vrai service.
@pytest.fixture
def memory_providers(tmp_path: Path) -> MemoryProviders:
    return fake_memory_providers(tmp_path)


@pytest.fixture
def app(settings: Settings, db_engine: AsyncEngine, memory_providers: MemoryProviders) -> FastAPI:
    # Dépend de `db_engine` pour que le schéma existe avant le lifespan.
    return create_app(settings, memory_providers=memory_providers)


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    # ASGITransport ne lance pas le lifespan : LifespanManager s'en charge.
    # raise_app_exceptions=False : une exception non gérée devient une réponse 500.
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


@pytest.fixture
async def client_google_mode(
    settings: Settings, db_engine: AsyncEngine, memory_providers: MemoryProviders
) -> AsyncIterator[httpx.AsyncClient]:
    # Mode `google` : aucune session n'existe encore (phase 9), les routes protégées répondent 401.
    google_app = create_app(
        settings.model_copy(update={"auth_mode": "google"}), memory_providers=memory_providers
    )
    async with LifespanManager(google_app):
        transport = httpx.ASGITransport(app=google_app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
