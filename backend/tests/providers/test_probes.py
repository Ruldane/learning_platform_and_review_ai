import httpx
import pytest
import respx

from app.providers.embeddings.ollama_probe import OllamaProbe
from app.providers.pdf.gotenberg_probe import GotenbergProbe
from app.providers.search.searxng_probe import SearxngProbe
from app.providers.vector.qdrant_probe import QdrantProbe

QDRANT = "http://qdrant:6333"
OLLAMA = "http://ollama:11434"
SEARXNG = "http://searxng:8080"
GOTENBERG = "http://gotenberg:3000"


@respx.mock
async def test_qdrant_ok(http: httpx.AsyncClient) -> None:
    respx.get(f"{QDRANT}/readyz").respond(200, text="all shards are ready")
    probe = QdrantProbe(QDRANT, http)
    assert (await probe.check()).ok and probe.name == "qdrant"


@respx.mock
async def test_qdrant_not_ready_is_reported(http: httpx.AsyncClient) -> None:
    respx.get(f"{QDRANT}/readyz").respond(503)
    status = await QdrantProbe(f"{QDRANT}/", http).check()
    assert not status.ok and "503" in status.detail


@respx.mock
async def test_qdrant_unreachable_raises_for_the_service(http: httpx.AsyncClient) -> None:
    respx.get(f"{QDRANT}/readyz").mock(side_effect=httpx.ConnectError("secret-detail"))
    with pytest.raises(httpx.ConnectError):
        await QdrantProbe(QDRANT, http).check()


@respx.mock
async def test_ollama_without_model_explains(http: httpx.AsyncClient) -> None:
    respx.get(f"{OLLAMA}/api/tags").respond(json={"models": []})
    s = await OllamaProbe(OLLAMA, "bge-m3", http).check()
    assert not s.ok and "bge-m3" in s.detail
    assert s.detail == "Le modèle bge-m3 est en cours de téléchargement."


@respx.mock
async def test_ollama_with_model_is_ok(http: httpx.AsyncClient) -> None:
    respx.get(f"{OLLAMA}/api/tags").respond(json={"models": [{"name": "bge-m3:latest"}]})
    assert (await OllamaProbe(OLLAMA, "bge-m3", http).check()).ok


@respx.mock
async def test_ollama_other_model_does_not_count(http: httpx.AsyncClient) -> None:
    respx.get(f"{OLLAMA}/api/tags").respond(json={"models": [{"name": "bge-m3-large:latest"}]})
    assert not (await OllamaProbe(OLLAMA, "bge-m3", http).check()).ok


@respx.mock
async def test_ollama_http_error_is_reported(http: httpx.AsyncClient) -> None:
    respx.get(f"{OLLAMA}/api/tags").respond(500)
    s = await OllamaProbe(OLLAMA, "bge-m3", http).check()
    assert not s.ok and "500" in s.detail


@respx.mock
async def test_searxng_json_disabled_is_explained(http: httpx.AsyncClient) -> None:
    respx.get(f"{SEARXNG}/healthz").respond(200)
    respx.get(url__startswith=f"{SEARXNG}/search").respond(403)
    s = await SearxngProbe(SEARXNG, http).check()
    assert not s.ok and "JSON" in s.detail
    assert s.detail == (
        "Le format JSON est peut-être désactivé dans SearXNG, "
        "ou la requête a été bloquée par son limiteur."
    )


@respx.mock
async def test_searxng_deep_check_has_its_own_longer_timeout(http: httpx.AsyncClient) -> None:
    respx.get(f"{SEARXNG}/healthz").respond(200)
    search = respx.get(url__startswith=f"{SEARXNG}/search").respond(json={"results": []})
    probe = SearxngProbe(SEARXNG, http)
    await probe.check()
    assert search.calls[0].request.extensions["timeout"]["read"] == 10.0
    # Le plafond demandé au service de santé couvre la sonde et la recherche profonde.
    assert probe.timeout > 10.0


@respx.mock
async def test_searxng_deep_check_runs_once_after_success(http: httpx.AsyncClient) -> None:
    health = respx.get(f"{SEARXNG}/healthz").respond(200, text="OK")
    search = respx.get(url__startswith=f"{SEARXNG}/search").respond(json={"results": []})
    probe = SearxngProbe(SEARXNG, http)
    assert (await probe.check()).ok and (await probe.check()).ok
    assert health.call_count == 2 and search.call_count == 1
    params = search.calls[0].request.url.params
    assert params["q"] == "tremplin" and params["format"] == "json"


@respx.mock
async def test_searxng_deep_check_is_retried_after_failure(http: httpx.AsyncClient) -> None:
    respx.get(f"{SEARXNG}/healthz").respond(200)
    search = respx.get(url__startswith=f"{SEARXNG}/search")
    search.side_effect = [httpx.Response(403), httpx.Response(200, json={"results": []})]
    probe = SearxngProbe(SEARXNG, http)
    assert not (await probe.check()).ok
    assert (await probe.check()).ok
    assert search.call_count == 2


@respx.mock
async def test_searxng_down_skips_the_deep_check(http: httpx.AsyncClient) -> None:
    respx.get(f"{SEARXNG}/healthz").respond(500)
    s = await SearxngProbe(SEARXNG, http).check()
    assert not s.ok and "500" in s.detail


@respx.mock
async def test_searxng_unexpected_search_status_is_reported(http: httpx.AsyncClient) -> None:
    respx.get(f"{SEARXNG}/healthz").respond(200)
    respx.get(url__startswith=f"{SEARXNG}/search").respond(500)
    s = await SearxngProbe(SEARXNG, http).check()
    assert not s.ok and "500" in s.detail


@respx.mock
async def test_gotenberg_ok_and_down(http: httpx.AsyncClient) -> None:
    route = respx.get(f"{GOTENBERG}/health")
    route.side_effect = [httpx.Response(200, json={"status": "up"}), httpx.Response(503)]
    probe = GotenbergProbe(GOTENBERG, http)
    assert probe.name == "gotenberg"
    assert (await probe.check()).ok
    down = await probe.check()
    assert not down.ok and "503" in down.detail
