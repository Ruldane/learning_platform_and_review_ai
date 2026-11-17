"""Revue finale 9.R (A-M3) : `api/tags` inattendu, `OllamaPullWatcher` ne lève jamais."""

import httpx
import pytest

from app.providers.embeddings.ollama_pull import OllamaPullWatcher

BASE = "http://ollama:11434"
MODEL = "bge-m3"


@pytest.mark.parametrize(
    "body",
    [
        b'{"models": 5}',
        b'{"models": "bge-m3"}',
        b'{"models": {"name": "bge-m3"}}',
        b"[1, 2]",
        b'{"models":' + b"[" * 100_000 + b"]" * 100_000 + b"}",  # JSON trop imbriqué
    ],
)
async def test_unexpected_tags_json_is_down_not_a_500(body: bytes) -> None:
    """Une réponse inattendue d'`api/tags` (type, imbrication) donne « Ollama ne répond pas »,
    jamais une exception sur la route publique."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body)

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    async with http:
        data = await OllamaPullWatcher(BASE, MODEL, http).progress()
    assert not data.present and data.detail == "Ollama ne répond pas."
