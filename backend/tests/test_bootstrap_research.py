"""Composition de la recherche web : clients dédiés, aucune requête à la construction, Brave
dans l'écran des clés."""

import httpx
import pytest
import respx
from asgi_lifespan import LifespanManager
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bootstrap import build_providers, key_test_http, research_providers
from app.config import Settings
from app.core.providers import ResearchProviders
from app.core.security import Cipher
from app.main import create_app
from app.providers.search.brave import BraveKeyProvider, BraveSearch
from app.providers.search.searxng import SearxngSearch
from app.providers.web.fetch import SafeHttpFetcher
from app.providers.web.transport import GuardedTransport
from tests.support.memory import FakeWebReader, fake_memory_providers
from tests.support.research import fake_research_providers


def _tracking(monkeypatch: pytest.MonkeyPatch) -> list[httpx.AsyncClient]:
    created: list[httpx.AsyncClient] = []
    original = httpx.AsyncClient

    def tracking(*args: object, **kwargs: object) -> httpx.AsyncClient:
        client = original(*args, **kwargs)  # type: ignore[arg-type]
        created.append(client)
        return client

    monkeypatch.setattr("app.bootstrap.httpx.AsyncClient", tracking)
    return created


async def test_research_providers_are_built_without_any_request(settings: Settings) -> None:
    web = FakeWebReader()
    configured = settings.model_copy(update={"searxng_url": "http://moteur:8080/"})
    with respx.mock(assert_all_called=False) as router:
        async with research_providers(configured, web) as built:
            assert isinstance(built, ResearchProviders) and built.web is web
            assert isinstance(built.searxng, SearxngSearch)
            assert built.searxng._base_url == "http://moteur:8080"  # type: ignore[attr-defined]
            brave = built.brave("BSA-cle-0001")
            assert isinstance(brave, BraveSearch) and brave.name == "brave"
        assert not router.calls


async def test_research_clients_are_dedicated_and_closed(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.interne:3128")
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.interne:3128")
    created = _tracking(monkeypatch)
    async with research_providers(settings, FakeWebReader()) as built:
        assert len(created) == 3 and not any(c.is_closed for c in created)
        searxng_http, brave_http, download_http = created
        assert built.searxng._http is searxng_http  # type: ignore[attr-defined]
        assert built.brave("BSA-cle-0001")._http is brave_http  # type: ignore[attr-defined]
        for client in (searxng_http, brave_http):
            assert client.follow_redirects is False and client.trust_env is False
            assert client.timeout == httpx.Timeout(10.0)
            assert not client._mounts  # aucun proxy repris de l'environnement
        # Copies locales des PDF (D91) : fetcher sûr sur le client durci du lecteur web.
        assert isinstance(built.fetcher, SafeHttpFetcher)
        assert built.fetcher._http is download_http
        assert isinstance(download_http._transport, GuardedTransport)
        assert download_http.follow_redirects is False and download_http.trust_env is False
        assert not download_http._mounts
    assert all(c.is_closed for c in created)


def test_build_providers_adds_brave_to_the_key_screen_only(
    settings: Settings, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    configured = settings.model_copy(update={"brave_api_key": "BSA-env-0001"})
    http, key_http = httpx.AsyncClient(), httpx.AsyncClient()
    built = build_providers(
        configured,
        db_session_factory,
        Cipher(Fernet.generate_key()),
        http,
        lambda: None,
        key_http=key_http,
    )
    assert list(built.key_providers) == ["anthropic", "openai", "glm", "brave"]
    brave = built.key_providers["brave"]
    # Revue 3.3 (c) : le test de la clé n'utilise pas le client des sondes.
    assert isinstance(brave, BraveKeyProvider) and brave._http is key_http
    assert "brave" not in built.llm
    assert built.env_keys["brave"] == "BSA-env-0001"


async def test_key_test_client_ignores_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.interne:3128")
    async with key_test_http() as http:
        assert http.follow_redirects is False and http.trust_env is False
        assert http.timeout == httpx.Timeout(10.0)
        assert not http._mounts


async def test_lifespan_gives_the_brave_key_test_its_own_client(
    settings: Settings, db_engine: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.interne:3128")
    memory = fake_memory_providers(settings.data_dir)
    app = create_app(
        settings,
        memory_providers=memory,
        research_providers=fake_research_providers(memory.web),
    )
    async with LifespanManager(app):
        brave = app.state.providers.key_providers["brave"]
        assert isinstance(brave, BraveKeyProvider)
        assert brave._http.trust_env is False and not brave._http._mounts
