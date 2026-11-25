"""Search through SearXNG (JSON API, `GET /search?format=json`), default provider and without
a key, reached on the internal Docker network. `format=json` must be in `search.formats`
(`infra/searxng/settings.yml`), otherwise SearXNG answers 403.

Response: `results[]` (`url`, `title`, `content`, `engine`, `publishedDate` in ISO 8601 or
`null`) and `unresponsive_engines` (pairs `[engine, error]`). Zero results with
unresponsive engines = SearXNG blocked or down: `SearchUnavailable`, so that the caller
falls back to Brave; zero results with no engine down = a real absence of results."""

import logging
from collections.abc import Sequence
from typing import Any

import httpx

from app.providers.search.base import (
    SEARCH_TIMEOUT_S,
    SearchResult,
    SearchUnavailable,
    TimeRange,
    is_web_url,
    keep_unique,
    text_or_empty,
)

logger = logging.getLogger(__name__)


def _params(
    query: str, lang: str | None, time_range: TimeRange | None, categories: Sequence[str]
) -> dict[str, str]:
    params = {"q": query, "format": "json"}
    if lang:
        params["language"] = lang
    if time_range:
        params["time_range"] = time_range
    if categories:
        params["categories"] = ",".join(categories)
    return params


def _result(item: dict[str, Any]) -> SearchResult:
    published = item.get("publishedDate")
    return SearchResult(
        title=text_or_empty(item.get("title")),
        url=item["url"],
        snippet=text_or_empty(item.get("content")),
        engine=text_or_empty(item.get("engine")),
        published=published if isinstance(published, str) and published else None,
    )


def _parse(body: object) -> list[SearchResult]:
    if not isinstance(body, dict) or not isinstance(body.get("results", []), list):
        logger.info("Unexpected SearXNG response")
        raise SearchUnavailable() from None
    items = [i for i in body.get("results", []) if isinstance(i, dict) and is_web_url(i.get("url"))]
    unresponsive = body.get("unresponsive_engines") or []
    if not items and not isinstance(unresponsive, list):
        # Review 3.3 (D74): unexpected shape, judged like engines down (fall back to Brave).
        logger.info("SearXNG without results, unresponsive engines of an unexpected shape")
        raise SearchUnavailable() from None
    if not items and unresponsive:
        logger.info("SearXNG without results, %d unresponsive engines", len(unresponsive))
        raise SearchUnavailable() from None
    return keep_unique([_result(i) for i in items])


class SearxngSearch:
    """`SearchProvider` on a dedicated client (`bootstrap.research_providers`)."""

    name = "searxng"

    def __init__(self, http: httpx.AsyncClient, base_url: str) -> None:
        self._http = http
        self._base_url = base_url.rstrip("/")

    async def search(
        self,
        query: str,
        *,
        lang: str | None = None,
        time_range: TimeRange | None = None,
        categories: Sequence[str] = (),
    ) -> list[SearchResult]:
        try:
            response = await self._http.get(
                f"{self._base_url}/search",
                params=_params(query, lang, time_range, categories),
                timeout=SEARCH_TIMEOUT_S,
            )
        except httpx.HTTPError as exc:
            # Type only: the message of an httpx error may quote the URL, hence the query.
            logger.info("SearXNG unreachable (%s)", type(exc).__name__)
            raise SearchUnavailable() from None
        if response.status_code != 200:
            logger.info("SearXNG refused the search (status %s)", response.status_code)
            raise SearchUnavailable() from None
        try:
            body = response.json()
        except ValueError:
            logger.info("Unreadable SearXNG response")
            raise SearchUnavailable() from None
        return _parse(body)
