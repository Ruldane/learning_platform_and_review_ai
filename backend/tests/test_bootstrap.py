from pathlib import Path

import httpx
import pytest
import respx
from asgi_lifespan import LifespanManager
from cryptography.fernet import Fernet
from qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bootstrap import _render_http, build_providers, memory_providers, page_renderer
from app.config import Settings
from app.core.providers import MemoryProviders, Providers
from app.core.security import Cipher
from app.main import create_app
from app.providers.embeddings.ollama import OllamaEmbedder
from app.providers.llm.glm import GlmProvider
from app.providers.pdf.gotenberg import GotenbergRenderer
from app.providers.pdf.subprocess import SubprocessPdfExtractor
from app.providers.storage.local import LocalFileStorage
from app.providers.vector.qdrant import QdrantMemoryRepository
from app.providers.web.reader import TrafilaturaWebReader
from app.providers.web.youtube import TranscriptApiYoutube

_HTTP = httpx.AsyncClient()


def _NO_USER() -> None:
    return None


def test_build_providers_registers_the_three_real_providers(
    settings: Settings, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    cipher = Cipher(Fernet.generate_key())
    built = build_providers(settings, db_session_factory, cipher, _HTTP, _NO_USER)
    assert isinstance(built, Providers) and built.cipher is cipher
    assert set(built.llm) == {"anthropic", "openai", "glm"} and "fake" not in built.llm


def test_env_keys_come_from_settings(
    settings: Settings, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    configured = settings.model_copy(
        update={"anthropic_api_key": "a-key-0001", "zai_api_key": "z-key-0002"}
    )
    built = build_providers(
        configured, db_session_factory, Cipher(Fernet.generate_key()), _HTTP, _NO_USER
    )
    assert dict(built.env_keys) == {
        "anthropic": "a-key-0001",
        "openai": None,
        "glm": "z-key-0002",
        "brave": None,
    }


def test_glm_honors_overridden_zai_base_url(
    settings: Settings, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    configured = settings.model_copy(update={"zai_base_url": "https://zai.example/v9/"})
    glm = build_providers(
        configured, db_session_factory, Cipher(Fernet.generate_key()), _HTTP, _NO_USER
    ).llm["glm"]
    assert isinstance(glm, GlmProvider)
    assert glm._url("models") == "https://zai.example/v9/models"


async def test_lifespan_stores_providers_and_serves_real_registry(
    settings: Settings, db_engine: object
) -> None:
    app = create_app(settings)
    async with LifespanManager(app):
        assert isinstance(app.state.providers, Providers)
        assert app.state.providers.cipher is app.state.cipher
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/api/v1/settings/api-keys")
    assert [e["provider"] for e in r.json()] == ["anthropic", "openai", "glm", "brave"]
    assert all(e["source"] is None for e in r.json())


async def test_memory_providers_are_built_without_any_request(settings: Settings) -> None:
    configured = settings.model_copy(
        update={"memory_collection": "ma_memoire", "embedding_dimension": 32}
    )
    with respx.mock(assert_all_called=False) as router:  # toute requête lèverait AllMockedError
        async with memory_providers(configured) as built:
            assert isinstance(built, MemoryProviders)
            assert isinstance(built.embedder, OllamaEmbedder)
            assert isinstance(built.index, QdrantMemoryRepository)
            assert isinstance(built.storage, LocalFileStorage)
            assert isinstance(built.pdf, SubprocessPdfExtractor)
            assert isinstance(built.web, TrafilaturaWebReader)
            assert isinstance(built.youtube, TranscriptApiYoutube)
        assert not router.calls


async def test_memory_providers_close_their_clients(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    created: list[httpx.AsyncClient] = []
    original = httpx.AsyncClient

    def tracking(*args: object, **kwargs: object) -> httpx.AsyncClient:
        client = original(*args, **kwargs)  # type: ignore[arg-type]
        created.append(client)
        return client

    closed: list[bool] = []

    async def close(self: AsyncQdrantClient) -> None:
        closed.append(True)

    monkeypatch.setattr("app.bootstrap.httpx.AsyncClient", tracking)
    monkeypatch.setattr(AsyncQdrantClient, "close", close)
    async with memory_providers(settings):
        assert len(created) == 2 and not any(c.is_closed for c in created)
    assert all(c.is_closed for c in created) and closed == [True]


async def test_web_reader_client_never_follows_redirects_nor_trusts_the_environment(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.interne:3128")
    created: list[httpx.AsyncClient] = []
    original = httpx.AsyncClient

    def tracking(*args: object, **kwargs: object) -> httpx.AsyncClient:
        client = original(*args, **kwargs)  # type: ignore[arg-type]
        created.append(client)
        return client

    monkeypatch.setattr("app.bootstrap.httpx.AsyncClient", tracking)
    async with memory_providers(settings) as built:
        reader = created[1]
        assert built.web._fetcher._http is reader  # type: ignore[attr-defined]
        assert reader.follow_redirects is False and reader.trust_env is False
        assert reader.timeout == httpx.Timeout(15.0)
        assert not reader._mounts  # aucun proxy repris de l'environnement


async def test_storage_lives_under_the_configured_data_dir(
    settings: Settings, tmp_path: Path
) -> None:
    configured = settings.model_copy(update={"data_dir": tmp_path})
    async with memory_providers(configured) as built:
        key = await built.storage.save("u1", "documents", b"x", ".txt")
    assert (tmp_path / "storage" / key).read_bytes() == b"x"


async def test_memory_providers_use_the_configured_services(settings: Settings) -> None:
    configured = settings.model_copy(
        update={
            "ollama_base_url": "http://autre:1234",
            "memory_collection": "c",
            "embedding_dimension": 8,
        }
    )
    with respx.mock as router:
        route = router.post("http://autre:1234/api/embed").respond(
            200, json={"embeddings": [[0.0] * 8]}
        )
        async with memory_providers(configured) as built:
            assert await built.embedder.aembed_query("x") == [0.0] * 8
        assert route.called


async def test_render_client_is_dedicated_and_ignores_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.interne:3128")
    async with _render_http() as http:
        assert http.follow_redirects is False and http.trust_env is False
        assert http.timeout == httpx.Timeout(15.0)
        assert not http._mounts


async def test_page_renderer_follows_the_settings(settings: Settings) -> None:
    configured = settings.model_copy(update={"gotenberg_url": "http://rendu:3000/"})
    assert configured.web_render_fallback is True
    async with _render_http() as http:
        renderer = page_renderer(configured, http)
        assert isinstance(renderer, GotenbergRenderer)
        assert renderer._endpoint == "http://rendu:3000/forms/chromium/convert/url"
        disabled = configured.model_copy(update={"web_render_fallback": False})
        assert page_renderer(disabled, http) is None


def test_web_render_fallback_is_read_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WEB_RENDER_FALLBACK", "false")
    assert Settings(_env_file=None).web_render_fallback is False  # type: ignore[call-arg]
