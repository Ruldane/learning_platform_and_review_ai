"""Recherche par SearXNG (API JSON, `GET /search?format=json`), fournisseur par défaut et sans
clé, joint sur le réseau Docker interne. `format=json` doit être dans `search.formats`
(`infra/searxng/settings.yml`), sinon SearXNG répond 403.

Réponse : `results[]` (`url`, `title`, `content`, `engine`, `publishedDate` en ISO 8601 ou
`null`) et `unresponsive_engines` (paires `[moteur, erreur]`). Zéro résultat avec des moteurs
non répondants = SearXNG bloqué ou en panne : `SearchUnavailable`, pour que l'appelant passe à
Brave ; zéro résultat sans moteur en panne = vraie absence de résultat."""

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
        logger.info("Réponse SearXNG inattendue")
        raise SearchUnavailable() from None
    items = [i for i in body.get("results", []) if isinstance(i, dict) and is_web_url(i.get("url"))]
    unresponsive = body.get("unresponsive_engines") or []
    if not items and unresponsive:
        logger.info("SearXNG sans résultat, %d moteurs sans réponse", len(unresponsive))
        raise SearchUnavailable() from None
    return keep_unique([_result(i) for i in items])


class SearxngSearch:
    """`SearchProvider` sur un client dédié (`bootstrap.research_providers`)."""

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
            # Type seul : le message d'une erreur httpx peut citer l'URL, donc la requête.
            logger.info("SearXNG injoignable (%s)", type(exc).__name__)
            raise SearchUnavailable() from None
        if response.status_code != 200:
            logger.info("SearXNG a refusé la recherche (statut %s)", response.status_code)
            raise SearchUnavailable() from None
        try:
            body = response.json()
        except ValueError:
            logger.info("Réponse SearXNG illisible")
            raise SearchUnavailable() from None
        return _parse(body)
