"""`GET /health/embedding` (P13) : progression du modèle d'embeddings, publique comme `/health`
(aucun cookie, y compris en mode Google). La source est remplacée : aucun appel à Ollama."""

import httpx
import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI

from app.config import Settings
from app.core.providers import MemoryProviders, PublishingProviders, ResearchProviders
from app.main import create_app
from app.providers.embeddings.base import EmbeddingProgressData
from app.providers.embeddings.ollama_pull import OllamaPullWatcher

# `google_app` (l'application en mode Google) est celle de la connexion, réimportée.
from tests.features.auth.conftest import google, google_app  # noqa: F401

URL = "/api/v1/health/embedding"


class FakeSource:
    def __init__(self, data: EmbeddingProgressData) -> None:
        self.data = data
        self.calls = 0

    async def progress(self) -> EmbeddingProgressData:
        self.calls += 1
        return self.data


DETAIL = "Téléchargement de bge-m3 en cours (42 %)."
DOWNLOADING = EmbeddingProgressData("bge-m3", False, 42, DETAIL)


async def test_embedding_route_reports_the_progress(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    source = FakeSource(DOWNLOADING)
    app.state.providers.embedding = source
    response = await client.get(URL)
    assert response.status_code == 200
    assert response.json() == {
        "model": "bge-m3",
        "present": False,
        "percent": 42,
        "detail": DETAIL,
    }
    assert source.calls == 1


async def test_embedding_route_unknown_size_is_null(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    app.state.providers.embedding = FakeSource(
        EmbeddingProgressData("bge-m3", False, None, "Ollama ne répond pas.")
    )
    body = (await client.get(URL)).json()
    assert body["percent"] is None and body["present"] is False


async def test_the_real_providers_watch_the_configured_model(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    # La composition (`build_providers`) pose le vrai suivi ; le lifespan l'a construit.
    assert isinstance(app.state.providers.embedding, OllamaPullWatcher)


async def test_embedding_route_public_in_google_mode(
    google_app: FastAPI,  # noqa: F811  (fixture de la connexion, réimportée ci-dessus)
) -> None:
    google_app.state.providers.embedding = FakeSource(DOWNLOADING)
    transport = httpx.ASGITransport(app=google_app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(URL)  # aucun cookie de session
        protected = await client.get("/api/v1/auth/me")
    assert response.status_code == 200 and response.json()["percent"] == 42
    assert protected.status_code == 401  # la porte est bien fermée ailleurs


async def test_the_embedding_watcher_is_closed_at_shutdown(
    settings: Settings,
    db_engine: object,
    memory_providers: MemoryProviders,
    research_providers: ResearchProviders,
    publishing_providers: PublishingProviders,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed: list[bool] = []

    async def spy(self: OllamaPullWatcher) -> None:
        closed.append(True)

    monkeypatch.setattr(OllamaPullWatcher, "aclose", spy, raising=False)
    app = create_app(
        settings,
        memory_providers=memory_providers,
        research_providers=research_providers,
        publishing_providers=publishing_providers,
    )
    async with LifespanManager(app):
        assert closed == []
    assert closed == [True]
