import json
import logging
from collections.abc import Callable

import httpx
import pytest

from app.providers.search.base import (
    MAX_RESULTS,
    SEARCH_TIMEOUT_S,
    SearchResult,
    SearchUnavailable,
)
from app.providers.search.searxng import SearxngSearch

_BASE = "http://searxng:8080"
_QUERY = "requête secrète de jeanne"


def _hit(url: str, title: str = "T", engine: str = "duckduckgo") -> dict[str, object]:
    return {"url": url, "title": title, "content": "c", "engine": engine, "publishedDate": None}


def _client(
    handler: Callable[[httpx.Request], httpx.Response], sent: list[httpx.Request] | None = None
) -> SearxngSearch:
    def record(request: httpx.Request) -> httpx.Response:
        if sent is not None:
            sent.append(request)
        return handler(request)

    http = httpx.AsyncClient(transport=httpx.MockTransport(record))
    return SearxngSearch(http, _BASE + "/")


def _json(body: dict[str, object], status: int = 200) -> Callable[[httpx.Request], httpx.Response]:
    return lambda request: httpx.Response(status, json=body)


async def test_searxng_sends_json_query_and_maps_results() -> None:
    sent: list[httpx.Request] = []
    body = {
        "results": [
            {
                "url": "https://ex.org/rag",
                "title": "RAG",
                "content": "extrait",
                "engine": "duckduckgo",
                "publishedDate": "2026-10-01T00:00:00",
            }
        ],
        "unresponsive_engines": [],
    }
    search = _client(_json(body), sent)
    hits = await search.search("rag", lang="fr", time_range="year", categories=["it", "science"])
    request = sent[-1]
    assert request.url.path == "/search" and request.url.host == "searxng"
    params = request.url.params
    assert params["q"] == "rag" and params["format"] == "json"
    assert params["language"] == "fr" and params["time_range"] == "year"
    assert params["categories"] == "it,science"
    assert request.extensions["timeout"]["read"] == SEARCH_TIMEOUT_S == 10.0
    assert hits[0] == SearchResult(
        "RAG", "https://ex.org/rag", "extrait", "duckduckgo", "2026-10-01T00:00:00"
    )
    assert search.name == "searxng"


async def test_searxng_omits_unset_optional_params() -> None:
    sent: list[httpx.Request] = []
    await _client(_json({"results": [], "unresponsive_engines": []}), sent).search("rag")
    assert set(sent[-1].url.params) == {"q", "format"}


async def test_searxng_drops_non_http_and_duplicate_urls() -> None:
    body = {
        "results": [
            _hit("https://ex.org/a", "A"),
            _hit("javascript:alert(1)"),
            _hit("ftp://ex.org/f"),
            {"title": "sans lien"},
            {"url": 42, "title": "lien invalide"},
            _hit("https://ex.org/a", "A bis"),
            _hit("http://ex.org/b", "B"),
            _hit("https:///sans-hote"),
        ],
        "unresponsive_engines": [],
    }
    hits = await _client(_json(body)).search("q")
    assert [(h.url, h.title) for h in hits] == [("https://ex.org/a", "A"), ("http://ex.org/b", "B")]


async def test_searxng_tolerates_missing_optional_fields() -> None:
    body = {"results": [{"url": "https://ex.org/x", "title": None, "publishedDate": 3}]}
    hits = await _client(_json(body)).search("q")
    assert hits == [SearchResult("", "https://ex.org/x", "", "", None)]


async def test_searxng_caps_results() -> None:
    body = {"results": [_hit(f"https://ex.org/{i}") for i in range(25)]}
    assert len(await _client(_json(body)).search("q")) == MAX_RESULTS


async def test_searxng_empty_without_unresponsive_engines_is_an_empty_list() -> None:
    body = {"results": [], "unresponsive_engines": []}
    assert await _client(_json(body)).search("q") == []


async def test_searxng_all_engines_unresponsive_is_unavailable() -> None:
    body = {
        "results": [],
        "unresponsive_engines": [["duckduckgo", "timeout"], ["brave", "CAPTCHA"]],
    }
    with pytest.raises(SearchUnavailable):
        await _client(_json(body)).search("q")


async def test_searxng_some_results_despite_unresponsive_engines() -> None:
    body = {"results": [_hit("https://ex.org/a")], "unresponsive_engines": [["brave", "timeout"]]}
    assert len(await _client(_json(body)).search("q")) == 1


async def test_searxng_403_is_unavailable_with_fixed_message(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    with pytest.raises(SearchUnavailable) as caught:
        await _client(_json({}, status=403)).search(_QUERY)
    error = caught.value
    assert error.code == "search_unavailable" and error.status_code == 503
    assert error.message == "La recherche web est indisponible pour le moment."
    assert error.__cause__ is None and error.__suppress_context__
    assert _QUERY not in caplog.text and "searxng:8080" not in caplog.text


@pytest.mark.parametrize(
    "handler",
    [
        lambda r: httpx.Response(500, json={}),
        lambda r: httpx.Response(200, content=b"<html>pas du json</html>"),
        lambda r: httpx.Response(200, json=["liste"]),
        lambda r: httpx.Response(200, json={"results": "pas une liste"}),
    ],
    ids=["500", "html", "json-liste", "results-invalides"],
)
async def test_searxng_bad_responses_are_unavailable(
    handler: Callable[[httpx.Request], httpx.Response],
) -> None:
    with pytest.raises(SearchUnavailable):
        await _client(handler).search("q")


@pytest.mark.parametrize("error", [httpx.ConnectError("x"), httpx.ReadTimeout("x")])
async def test_searxng_network_errors_are_unavailable(
    error: Exception, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)

    def boom(request: httpx.Request) -> httpx.Response:
        raise error

    with pytest.raises(SearchUnavailable) as caught:
        await _client(boom).search(_QUERY)
    assert caught.value.__cause__ is None
    assert _QUERY not in caplog.text and json.dumps(_QUERY) not in caplog.text
