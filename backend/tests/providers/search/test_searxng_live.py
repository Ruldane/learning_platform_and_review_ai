"""Recherche contre un vrai SearXNG : marqué `live`, désélectionné par défaut (`-m 'not live'`).

SearXNG n'a aucun port publié (réseau Docker interne) : lancer depuis le conteneur du back, par
exemple `docker compose exec backend uv run python -m pytest -m live
tests/providers/search/test_searxng_live.py` (`SEARXNG_URL` y vaut `http://searxng:8080`).
"""

import os

import httpx
import pytest

from app.providers.search.searxng import SearxngSearch

pytestmark = pytest.mark.live


async def test_searxng_live_returns_results() -> None:
    url = os.environ.get("SEARXNG_URL")
    if not url:
        pytest.skip("SEARXNG_URL n'est pas définie")
    async with httpx.AsyncClient(trust_env=False) as http:
        hits = await SearxngSearch(http, url).search("python asyncio", lang="en")
    assert hits and all(h.url.startswith(("http://", "https://")) for h in hits)
    assert len({h.url for h in hits}) == len(hits)
