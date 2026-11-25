import hashlib
import json
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.db.models.research import CacheKind, PageStatus
from app.features.memory.service.upload import normalize_url
from app.features.research.repository import WebCacheRepository
from app.providers.search.base import SearchResult

PAGE_TTL = timedelta(days=7)
UNREADABLE_TTL = timedelta(hours=24)
SEARCH_TTL = timedelta(hours=24)


@dataclass(frozen=True)
class CachedPage:
    status: PageStatus
    title: str | None
    text: str
    author: str | None
    date: str | None
    lang: str | None
    reason: str | None


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def url_key(url: str) -> str:
    """Fingerprint of the normalized URL (D66): scheme and host in lowercase, without fragment.
    Raises the error of `normalize_url` for a link that is not http(s)."""
    return _sha256(normalize_url(url))


def _page_key(url: str, client: bool) -> str:
    return _sha256(f"mcp:{normalize_url(url)}") if client else url_key(url)


def search_key(
    provider: str,
    query: str,
    lang: str | None,
    time_range: str | None,
    categories: Sequence[str],
) -> str:
    """Fingerprint of a search: case and spaces of the query, category order ignored."""
    words = " ".join(query.split()).casefold()
    parts = [provider, words, lang, time_range, sorted(categories)]
    return _sha256(json.dumps(parts, ensure_ascii=False, separators=(",", ":")))


class WebCache:
    """A user's web cache: a page read is kept 7 days, an unreadable page and a result list 24 h
    (SPEC 10.1, 10.2). Logs nothing; the stored keys are fingerprints."""

    def __init__(
        self, db: AsyncSession, user_id: str, *, now: Callable[[], datetime] = utcnow
    ) -> None:
        self._repo = WebCacheRepository(db, user_id)
        self._now = now

    async def _get(self, kind: CacheKind, key: str) -> dict[str, Any] | None:
        entry = await self._repo.get(kind, key, self._now())
        return entry.payload if entry is not None else None

    async def get_page(self, url: str, *, client: bool = False) -> CachedPage | None:
        key = _page_key(url, client)
        payload = await self._get("page", key)
        if payload is None:
            return None
        try:
            return CachedPage(**payload)
        except TypeError:
            return None  # entry in an old form: as if it did not exist

    async def put_page(self, url: str, page: CachedPage, *, client: bool = False) -> None:
        ttl = PAGE_TTL if page.status == "ok" else UNREADABLE_TTL
        await self._repo.put(
            "page", _page_key(url, client), page.status, asdict(page), self._now() + ttl
        )

    async def get_search(self, key: str) -> list[SearchResult] | None:
        payload = await self._get("search", key)
        if payload is None:
            return None
        try:
            return [SearchResult(**item) for item in payload["results"]]
        except (KeyError, TypeError):
            return None

    async def put_search(self, key: str, results: Sequence[SearchResult]) -> None:
        """Keeps the list for 24 h. The caller does not store an empty list caused by a failure."""
        payload = {"results": [asdict(result) for result in results]}
        await self._repo.put("search", key, "ok", payload, self._now() + SEARCH_TTL)
