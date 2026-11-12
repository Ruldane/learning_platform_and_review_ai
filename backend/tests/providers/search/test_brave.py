import logging
from collections.abc import Callable

import httpx
import pytest

from app.providers.search.base import SEARCH_TIMEOUT_S, SearchResult, SearchUnavailable
from app.providers.search.brave import BRAVE_SEARCH_URL, BraveKeyProvider, BraveSearch

_KEY = "secret-brave-key-1234"
_QUERY = "requête secrète de jeanne"
Handler = Callable[[httpx.Request], httpx.Response]


def _http(handler: Handler, sent: list[httpx.Request] | None = None) -> httpx.AsyncClient:
    def record(request: httpx.Request) -> httpx.Response:
        if sent is not None:
            sent.append(request)
        return handler(request)

    return httpx.AsyncClient(transport=httpx.MockTransport(record))


def _web(*results: dict[str, object]) -> Handler:
    return lambda request: httpx.Response(200, json={"web": {"results": list(results)}})


async def test_brave_sends_token_header_and_maps_results() -> None:
    sent: list[httpx.Request] = []
    handler = _web(
        {
            "title": "RAG <strong>expliqué</strong>",
            "url": "https://ex.org/rag",
            "description": "Le <strong>RAG</strong> &amp; la recherche",
            "page_age": "2026-10-01T00:00:00",
            "age": "il y a 1 mois",
        }
    )
    search = BraveSearch(_http(handler, sent), _KEY)
    hits = await search.search("rag", lang="fr", time_range="month", categories=["it"])
    request = sent[-1]
    assert str(request.url).startswith(BRAVE_SEARCH_URL + "?")
    assert request.headers["X-Subscription-Token"] == _KEY
    assert request.headers["Accept"] == "application/json"
    params = request.url.params
    assert params["q"] == "rag" and params["count"] == "10"
    assert params["search_lang"] == "fr" and params["freshness"] == "pm"
    assert "categories" not in params
    assert request.extensions["timeout"]["read"] == SEARCH_TIMEOUT_S
    assert hits == [
        SearchResult(
            "RAG expliqué",
            "https://ex.org/rag",
            "Le RAG & la recherche",
            "brave",
            "2026-10-01T00:00:00",
        )
    ]
    assert search.name == "brave"


@pytest.mark.parametrize(
    ("time_range", "freshness"), [("day", "pd"), ("week", "pw"), ("month", "pm"), ("year", "py")]
)
async def test_brave_maps_time_ranges(time_range: str, freshness: str) -> None:
    sent: list[httpx.Request] = []
    await BraveSearch(_http(_web(), sent), _KEY).search("q", time_range=time_range)  # type: ignore[arg-type]
    assert sent[-1].url.params["freshness"] == freshness


async def test_brave_maps_languages_and_omits_unset_params() -> None:
    sent: list[httpx.Request] = []
    search = BraveSearch(_http(_web(), sent), _KEY)
    await search.search("q")
    assert set(sent[-1].url.params) == {"q", "count"}
    await search.search("q", lang="pt")
    assert sent[-1].url.params["search_lang"] == "pt-pt"


async def test_brave_drops_non_http_and_duplicate_urls() -> None:
    handler = _web(
        {"title": "A", "url": "https://ex.org/a", "description": "d"},
        {"title": "X", "url": "javascript:alert(1)"},
        {"title": "A bis", "url": "https://ex.org/a"},
        {"title": "sans lien"},
    )
    hits = await BraveSearch(_http(handler), _KEY).search("q")
    assert [h.url for h in hits] == ["https://ex.org/a"]


async def test_brave_without_web_section_is_an_empty_list() -> None:
    handler: Handler = lambda request: httpx.Response(200, json={"type": "search"})  # noqa: E731
    assert await BraveSearch(_http(handler), _KEY).search("q") == []


@pytest.mark.parametrize("status", [401, 403, 422, 429, 500, 503])
async def test_brave_errors_never_contain_the_key(
    status: int, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    handler: Handler = lambda request: httpx.Response(  # noqa: E731
        status, json={"error": {"detail": f"bad token {_KEY}"}}
    )
    with pytest.raises(SearchUnavailable) as caught:
        await BraveSearch(_http(handler), _KEY).search(_QUERY)
    error = caught.value
    assert _KEY not in error.message + caplog.text and _QUERY not in caplog.text
    assert error.__cause__ is None and error.__suppress_context__


@pytest.mark.parametrize("error", [httpx.ConnectError("x"), httpx.ReadTimeout("x")])
async def test_brave_network_errors_are_unavailable(
    error: Exception, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)

    def boom(request: httpx.Request) -> httpx.Response:
        raise error

    with pytest.raises(SearchUnavailable) as caught:
        await BraveSearch(_http(boom), _KEY).search(_QUERY)
    assert caught.value.__cause__ is None
    assert _KEY not in caplog.text and _QUERY not in caplog.text


async def test_brave_invalid_json_is_unavailable() -> None:
    handler: Handler = lambda request: httpx.Response(200, content=b"<html>")  # noqa: E731
    with pytest.raises(SearchUnavailable):
        await BraveSearch(_http(handler), _KEY).search("q")


async def test_brave_non_ascii_key_is_unavailable_without_request() -> None:
    sent: list[httpx.Request] = []
    with pytest.raises(SearchUnavailable):
        await BraveSearch(_http(_web(), sent), "clé-é-invalide").search("q")
    assert sent == []


async def test_brave_key_test_sends_minimal_request_and_reports_ok() -> None:
    sent: list[httpx.Request] = []
    provider = BraveKeyProvider(_http(_web(), sent))
    result = await provider.test_key(_KEY)
    assert result.ok is True and result.message == "Clé valide."
    assert provider.name == "brave" and provider.label == "Brave Search"
    params = sent[-1].url.params
    assert params["count"] == "1" and sent[-1].headers["X-Subscription-Token"] == _KEY


@pytest.mark.parametrize(
    ("status", "body", "expected"),
    [
        (401, {}, "Clé refusée par Brave Search."),
        (403, {}, "Clé refusée par Brave Search."),
        (
            422,
            {"error": {"code": "SUBSCRIPTION_TOKEN_INVALID", "detail": _KEY}},
            "Clé refusée par Brave Search.",
        ),
        (429, {}, "Limite de requêtes atteinte chez Brave Search, réessaie plus tard."),
        (500, {"error": {"detail": _KEY}}, "Brave Search a répondu par une erreur (500)."),
    ],
)
async def test_brave_key_test_reports_invalid_key(
    status: int, body: dict[str, object], expected: str
) -> None:
    handler: Handler = lambda request: httpx.Response(status, json=body)  # noqa: E731
    result = await BraveKeyProvider(_http(handler)).test_key(_KEY)
    assert result.ok is False and result.message == expected


async def test_brave_key_test_never_raises() -> None:
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"connexion refusée {_KEY}")

    result = await BraveKeyProvider(_http(boom)).test_key(_KEY)
    assert result.ok is False and _KEY not in result.message
    assert result.message == "Impossible de joindre Brave Search. Vérifie ta connexion."
    invalid = await BraveKeyProvider(_http(_web())).test_key("clé-é")
    assert invalid.ok is False and invalid.message == "La clé contient des caractères invalides."
