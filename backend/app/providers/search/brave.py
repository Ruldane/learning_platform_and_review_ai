"""Search through the Brave Search API (`GET /res/v1/web/search`), fallback for SearXNG, one key
per user (`X-Subscription-Token`). Parameters: `q`, `count` (20 at most), `search_lang`,
`freshness` (`pd`, `pw`, `pm`, `py`). Response: `web.results[]` (`title`, `url`, `description`
with `<strong>` tags, `page_age` in ISO 8601; `age` is free text, ignored).

The key appears in no message, no log and no exception string: a failure only
keeps the HTTP status or the error type (the body of a Brave response may quote the key)."""

import html
import logging
import re
from collections.abc import Sequence
from typing import Any

import httpx

from app.providers.keys import KeyTestResult
from app.providers.search.base import (
    MAX_RESULTS,
    SEARCH_TIMEOUT_S,
    SearchNotServed,
    SearchResult,
    SearchUnavailable,
    TimeRange,
    is_web_url,
    keep_unique,
    text_or_empty,
)

logger = logging.getLogger(__name__)

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
_LABEL = "Brave Search"
_FRESHNESS: dict[str, str] = {"day": "pd", "week": "pw", "month": "pm", "year": "py"}
# Brave language codes that differ from the ISO 639-1 used by the settings.
_LANGS = {"pt": "pt-pt", "ja": "jp", "zh": "zh-hans"}
_TAG = re.compile(r"<[^>]{0,200}>")
# Invalid key: Brave answers 401/403, or 422 with this code in the body.
_INVALID_TOKEN_CODES = ("SUBSCRIPTION_TOKEN_INVALID",)
# Responses that Brave does not bill: rate exceeded (1 request per second on the free plan),
# key refused. The other failures stay counted (caution, D76).
_NOT_BILLED_STATUSES = (401, 403, 429)
# Errors raised before the request is sent: nothing left.
_NOT_SENT_ERRORS = (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout)


def _plain(value: object) -> str:
    """Text without the highlight tags (`<strong>`) or HTML entities."""
    return html.unescape(_TAG.sub("", text_or_empty(value))).strip()


def _headers(api_key: str) -> dict[str, str] | None:
    """Headers, or `None` if the key is not printable ASCII (httpx would raise while quoting
    the header)."""
    if not (api_key.isascii() and api_key.isprintable()):
        return None
    return {"X-Subscription-Token": api_key, "Accept": "application/json"}


def _params(query: str, lang: str | None, time_range: TimeRange | None) -> dict[str, str]:
    params = {"q": query, "count": str(MAX_RESULTS)}
    if lang:
        params["search_lang"] = _LANGS.get(lang, lang)
    if time_range:
        params["freshness"] = _FRESHNESS[time_range]
    return params


def _result(item: dict[str, Any]) -> SearchResult:
    published = item.get("page_age")
    return SearchResult(
        title=_plain(item.get("title")),
        url=item["url"],
        snippet=_plain(item.get("description")),
        engine="brave",
        published=published if isinstance(published, str) and published else None,
    )


def _parse(body: object) -> list[SearchResult]:
    """Without a `web` section: no result. A body that is not an object, `web` or
    `web.results` of an unexpected shape: unavailable (review 3.3, D74)."""
    web = body.get("web", {}) if isinstance(body, dict) else None
    items = web.get("results", []) if isinstance(web, dict) else None
    if not isinstance(items, list):
        logger.info("Unexpected Brave response")
        raise SearchUnavailable() from None
    valid = [i for i in items if isinstance(i, dict) and is_web_url(i.get("url"))]
    return keep_unique([_result(i) for i in valid])


class BraveSearch:
    """`SearchProvider` for one key: built by the `ResearchProviders.brave` factory."""

    name = "brave"

    def __init__(self, http: httpx.AsyncClient, api_key: str) -> None:
        self._http = http
        self._api_key = api_key

    async def search(
        self,
        query: str,
        *,
        lang: str | None = None,
        time_range: TimeRange | None = None,
        categories: Sequence[str] = (),
    ) -> list[SearchResult]:
        """`categories` is ignored: Brave's web API has no categories."""
        headers = _headers(self._api_key)
        if headers is None:
            logger.info("Invalid Brave key (characters)")
            raise SearchNotServed() from None
        try:
            response = await self._http.get(
                BRAVE_SEARCH_URL,
                params=_params(query, lang, time_range),
                headers=headers,
                timeout=SEARCH_TIMEOUT_S,
            )
        except httpx.HTTPError as exc:
            logger.info("Brave unreachable (%s)", type(exc).__name__)
            if isinstance(exc, _NOT_SENT_ERRORS):
                raise SearchNotServed() from None
            raise SearchUnavailable() from None
        if response.status_code != 200:
            logger.info("Brave refused the search (status %s)", response.status_code)
            if response.status_code in _NOT_BILLED_STATUSES:
                raise SearchNotServed() from None
            raise SearchUnavailable() from None
        try:
            body = response.json()
        except ValueError:
            logger.info("Unreadable Brave response")
            raise SearchUnavailable() from None
        return _parse(body)


def _error_code(response: httpx.Response) -> str | None:
    """Error code of the body (`{"error": {"code"}}`), the only element of the body we read."""
    try:
        code = response.json()["error"]["code"]
    except (ValueError, KeyError, TypeError):
        return None
    return code if isinstance(code, str) else None


def _test_message(response: httpx.Response) -> KeyTestResult:
    status = response.status_code
    if status == 200:
        return KeyTestResult(ok=True, message="API key is valid.")
    if status in (401, 403) or _error_code(response) in _INVALID_TOKEN_CODES:
        return KeyTestResult(ok=False, message=f"{_LABEL} rejected the API key.")
    if status == 429:
        return KeyTestResult(
            ok=False, message=f"{_LABEL}'s request limit was reached. Try again later."
        )
    return KeyTestResult(ok=False, message=f"{_LABEL} returned an error ({status}).")


class BraveKeyProvider:
    """Test of the Brave key for the keys screen (`KeyProvider`): a minimal search
    (`count=1`), outside the counter of the 900 monthly requests (D73). Never raises."""

    name = "brave"
    label = _LABEL

    def __init__(self, http: httpx.AsyncClient) -> None:
        self._http = http

    async def test_key(self, api_key: str) -> KeyTestResult:
        headers = _headers(api_key)
        if headers is None:
            return KeyTestResult(ok=False, message="The API key contains invalid characters.")
        try:
            response = await self._http.get(
                BRAVE_SEARCH_URL,
                params={"q": "tremplin", "count": "1"},
                headers=headers,
                timeout=SEARCH_TIMEOUT_S,
            )
        except httpx.HTTPError as exc:
            logger.info("Brave key test: unreachable (%s)", type(exc).__name__)
            return KeyTestResult(
                ok=False, message=f"Could not reach {_LABEL}. Check your connection."
            )
        return _test_message(response)
