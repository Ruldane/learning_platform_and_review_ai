"""Journaux sans aucune URL, redirections comprises (spec 17.2 : une URL peut porter un jeton)."""

import logging

import httpx
import pytest

from app.core.logging import configure_logging
from tests.providers.web.fetch_support import fetcher_for, html, redirect

URL = "https://example.com/depart?jeton=secret-jeton"


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/arrivee":
        return html()
    return redirect("https://example.org/arrivee?jeton=secret-relai")


async def _fetch() -> None:
    fetcher, client = fetcher_for(_handler)
    async with client:
        await fetcher.fetch(URL)


async def test_httpx_would_log_the_url_without_configuration(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Témoin : sans `configure_logging`, httpx écrit bien l'URL en INFO."""
    logging.getLogger("httpx").setLevel(logging.INFO)
    try:
        caplog.set_level(logging.INFO)
        await _fetch()
        assert "secret-jeton" in caplog.text
    finally:
        configure_logging("INFO", lambda: [])


async def test_fetch_with_a_redirect_never_logs_a_url(caplog: pytest.LogCaptureFixture) -> None:
    configure_logging("INFO", lambda: [])
    caplog.set_level(logging.DEBUG)
    await _fetch()
    assert "secret-jeton" not in caplog.text and "secret-relai" not in caplog.text
    assert "example.com" not in caplog.text and "example.org" not in caplog.text
