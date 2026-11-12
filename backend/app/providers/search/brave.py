"""Recherche par l'API Brave Search (`GET /res/v1/web/search`), secours de SearXNG, une clé par
utilisateur (`X-Subscription-Token`). Paramètres : `q`, `count` (20 au plus), `search_lang`,
`freshness` (`pd`, `pw`, `pm`, `py`). Réponse : `web.results[]` (`title`, `url`, `description`
avec des balises `<strong>`, `page_age` en ISO 8601 ; `age` est un texte libre, ignoré).

La clé n'apparaît dans aucun message, aucun journal ni aucune chaîne d'exception : un échec ne
garde que le statut HTTP ou le type d'erreur (le corps d'une réponse Brave peut citer la clé)."""

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
# Codes de langue Brave qui diffèrent de l'ISO 639-1 utilisé par les réglages.
_LANGS = {"pt": "pt-pt", "ja": "jp", "zh": "zh-hans"}
_TAG = re.compile(r"<[^>]{0,200}>")
# Clé invalide : Brave répond 401/403, ou 422 avec ce code dans le corps.
_INVALID_TOKEN_CODES = ("SUBSCRIPTION_TOKEN_INVALID",)


def _plain(value: object) -> str:
    """Texte sans les balises de mise en relief (`<strong>`) ni les entités HTML."""
    return html.unescape(_TAG.sub("", text_or_empty(value))).strip()


def _headers(api_key: str) -> dict[str, str] | None:
    """En-têtes, ou `None` si la clé n'est pas de l'ASCII imprimable (httpx lèverait en citant
    l'en-tête)."""
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
    web = body.get("web") if isinstance(body, dict) else None
    items = web.get("results") if isinstance(web, dict) else []
    if not isinstance(items, list):
        logger.info("Réponse Brave inattendue")
        raise SearchUnavailable() from None
    valid = [i for i in items if isinstance(i, dict) and is_web_url(i.get("url"))]
    return keep_unique([_result(i) for i in valid])


class BraveSearch:
    """`SearchProvider` pour une clé : construit par la fabrique `ResearchProviders.brave`."""

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
        """`categories` est ignoré : l'API web de Brave n'a pas de catégories."""
        headers = _headers(self._api_key)
        if headers is None:
            logger.info("Clé Brave invalide (caractères)")
            raise SearchUnavailable() from None
        try:
            response = await self._http.get(
                BRAVE_SEARCH_URL,
                params=_params(query, lang, time_range),
                headers=headers,
                timeout=SEARCH_TIMEOUT_S,
            )
        except httpx.HTTPError as exc:
            logger.info("Brave injoignable (%s)", type(exc).__name__)
            raise SearchUnavailable() from None
        if response.status_code != 200:
            logger.info("Brave a refusé la recherche (statut %s)", response.status_code)
            raise SearchUnavailable() from None
        try:
            body = response.json()
        except ValueError:
            logger.info("Réponse Brave illisible")
            raise SearchUnavailable() from None
        return _parse(body)


def _error_code(response: httpx.Response) -> str | None:
    """Code d'erreur du corps (`{"error": {"code"}}`), seul élément du corps qu'on lit."""
    try:
        code = response.json()["error"]["code"]
    except (ValueError, KeyError, TypeError):
        return None
    return code if isinstance(code, str) else None


def _test_message(response: httpx.Response) -> KeyTestResult:
    status = response.status_code
    if status == 200:
        return KeyTestResult(ok=True, message="Clé valide.")
    if status in (401, 403) or _error_code(response) in _INVALID_TOKEN_CODES:
        return KeyTestResult(ok=False, message=f"Clé refusée par {_LABEL}.")
    if status == 429:
        return KeyTestResult(
            ok=False, message=f"Limite de requêtes atteinte chez {_LABEL}, réessaie plus tard."
        )
    return KeyTestResult(ok=False, message=f"{_LABEL} a répondu par une erreur ({status}).")


class BraveKeyProvider:
    """Test de la clé Brave pour l'écran des clés (`KeyProvider`) : une recherche minimale
    (`count=1`), hors du compteur des 900 requêtes mensuelles (D73). Ne lève jamais."""

    name = "brave"
    label = _LABEL

    def __init__(self, http: httpx.AsyncClient) -> None:
        self._http = http

    async def test_key(self, api_key: str) -> KeyTestResult:
        headers = _headers(api_key)
        if headers is None:
            return KeyTestResult(ok=False, message="La clé contient des caractères invalides.")
        try:
            response = await self._http.get(
                BRAVE_SEARCH_URL,
                params={"q": "tremplin", "count": "1"},
                headers=headers,
                timeout=SEARCH_TIMEOUT_S,
            )
        except httpx.HTTPError as exc:
            logger.info("Test de la clé Brave : injoignable (%s)", type(exc).__name__)
            return KeyTestResult(
                ok=False, message=f"Impossible de joindre {_LABEL}. Vérifie ta connexion."
            )
        return _test_message(response)
