"""Composition de la recherche web : clients dédiés, aucune requête à la construction, Brave
dans l'écran des clés."""

import httpx
import pytest
import respx
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bootstrap import build_providers, research_providers
from app.config import Settings
from app.core.providers import ResearchProviders
from app.core.security import Cipher
from app.providers.search.brave import BraveKeyProvider, BraveSearch
from app.providers.search.searxng import SearxngSearch
from tests.support.memory import FakeWebReader


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
        assert len(created) == 2 and not any(c.is_closed for c in created)
        searxng_http, brave_http = created
        assert built.searxng._http is searxng_http  # type: ignore[attr-defined]
        assert built.brave("BSA-cle-0001")._http is brave_http  # type: ignore[attr-defined]
        for client in created:
            assert client.follow_redirects is False and client.trust_env is False
            assert client.timeout == httpx.Timeout(10.0)
            assert not client._mounts  # aucun proxy repris de l'environnement
    assert all(c.is_closed for c in created)


def test_build_providers_adds_brave_to_the_key_screen_only(
    settings: Settings, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    configured = settings.model_copy(update={"brave_api_key": "BSA-env-0001"})
    http = httpx.AsyncClient()
    built = build_providers(
        configured, db_session_factory, Cipher(Fernet.generate_key()), http, lambda: None
    )
    assert list(built.key_providers) == ["anthropic", "openai", "glm", "brave"]
    brave = built.key_providers["brave"]
    assert isinstance(brave, BraveKeyProvider) and brave._http is http
    assert "brave" not in built.llm
    assert built.env_keys["brave"] == "BSA-env-0001"
