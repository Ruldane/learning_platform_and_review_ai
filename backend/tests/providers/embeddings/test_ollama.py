import json

import httpx
import pytest
import respx

from app.providers.embeddings.base import EmbeddingsUnavailable
from app.providers.embeddings.ollama import OllamaEmbedder

URL = "http://ollama:11434/api/embed"
BASE = "http://ollama:11434"


def _echo_embeddings(dim: int):  # type: ignore[no-untyped-def]
    def handler(request: httpx.Request) -> httpx.Response:
        texts = json.loads(request.content)["input"]
        return httpx.Response(200, json={"embeddings": [[float(len(t))] * dim for t in texts]})

    return handler


@pytest.fixture
async def http() -> httpx.AsyncClient:
    async with httpx.AsyncClient(timeout=3.0) as client:
        yield client  # type: ignore[misc]


@respx.mock
async def test_ollama_embeds_in_batches_of_16(http: httpx.AsyncClient) -> None:
    route = respx.post(URL).mock(side_effect=_echo_embeddings(3))
    out = await OllamaEmbedder(BASE, "bge-m3", http).aembed_documents([f"t{i}" for i in range(20)])
    assert len(out) == 20 and all(len(v) == 3 for v in out)
    sizes = [len(json.loads(c.request.content)["input"]) for c in route.calls]
    assert sizes == [16, 4]
    assert json.loads(route.calls[0].request.content)["model"] == "bge-m3"


@respx.mock
async def test_ollama_keeps_order_across_batches(http: httpx.AsyncClient) -> None:
    respx.post(URL).mock(side_effect=_echo_embeddings(1))
    texts = ["a" * (i + 1) for i in range(20)]
    out = await OllamaEmbedder(BASE, "bge-m3", http).aembed_documents(texts)
    assert [v[0] for v in out] == [float(i + 1) for i in range(20)]


@respx.mock
async def test_ollama_no_texts_makes_no_request(http: httpx.AsyncClient) -> None:
    route = respx.post(URL)
    assert await OllamaEmbedder(BASE, "bge-m3", http).aembed_documents([]) == []
    assert not route.called


@respx.mock
async def test_ollama_query_returns_one_vector(http: httpx.AsyncClient) -> None:
    respx.post(URL).mock(side_effect=_echo_embeddings(2))
    assert await OllamaEmbedder(f"{BASE}/", "bge-m3", http).aembed_query("abc") == [3.0, 3.0]


@respx.mock
async def test_ollama_unreachable_raises_readable_503(http: httpx.AsyncClient) -> None:
    respx.post(URL).mock(side_effect=httpx.ConnectError("secret-detail"))
    with pytest.raises(EmbeddingsUnavailable) as caught:
        await OllamaEmbedder(BASE, "bge-m3", http).aembed_query("x")
    assert caught.value.status_code == 503 and caught.value.code == "embeddings_unavailable"
    assert "Ollama" in caught.value.message and "bge-m3" in caught.value.message
    assert "secret-detail" not in caught.value.message
    assert caught.value.__cause__ is None


@respx.mock
@pytest.mark.parametrize("status", [404, 500, 503, 400])
async def test_ollama_http_errors_become_unavailable(http: httpx.AsyncClient, status: int) -> None:
    respx.post(URL).respond(status, json={"error": "model 'bge-m3' not found"})
    with pytest.raises(EmbeddingsUnavailable) as caught:
        await OllamaEmbedder(BASE, "bge-m3", http).aembed_documents(["x"])
    assert caught.value.status_code == 503 and "not found" not in caught.value.message


@respx.mock
async def test_ollama_timeout_becomes_unavailable(http: httpx.AsyncClient) -> None:
    respx.post(URL).mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(EmbeddingsUnavailable):
        await OllamaEmbedder(BASE, "bge-m3", http).aembed_documents(["x"])


@respx.mock
async def test_ollama_inconsistent_vector_count_is_unavailable(http: httpx.AsyncClient) -> None:
    respx.post(URL).respond(200, json={"embeddings": [[0.1]]})
    with pytest.raises(EmbeddingsUnavailable):
        await OllamaEmbedder(BASE, "bge-m3", http).aembed_documents(["a", "b"])


@respx.mock
@pytest.mark.parametrize("body", [{"nope": 1}, {"embeddings": "x"}, {"embeddings": [["a"]]}])
async def test_ollama_malformed_body_is_unavailable(
    http: httpx.AsyncClient, body: dict[str, object]
) -> None:
    respx.post(URL).respond(200, json=body)
    with pytest.raises(EmbeddingsUnavailable):
        await OllamaEmbedder(BASE, "bge-m3", http).aembed_documents(["a"])


@respx.mock
async def test_ollama_non_json_body_is_unavailable(http: httpx.AsyncClient) -> None:
    respx.post(URL).respond(200, text="<html>")
    with pytest.raises(EmbeddingsUnavailable):
        await OllamaEmbedder(BASE, "bge-m3", http).aembed_documents(["a"])
