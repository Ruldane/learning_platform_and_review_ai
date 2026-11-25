"""Web search port (SPEC 10.1): shared types, limits and the single error.

No error message or log quotes the query, a URL or a key (SPEC 17.2): the
implementations only log their name, an HTTP status or an exception type."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol
from urllib.parse import urlsplit

from app.core.errors import AppError

TimeRange = Literal["day", "week", "month", "year"]
SEARCH_CATEGORIES = ("general", "it", "science", "videos")
MAX_RESULTS = 10
# Timeout of a search (SearXNG queries its engines in parallel, Brave answers fast).
SEARCH_TIMEOUT_S = 10.0


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str
    engine: str
    published: str | None


class SearchUnavailable(AppError):
    """Provider unreachable, in error or with no engine that answers: fixed message."""

    def __init__(self) -> None:
        super().__init__("search_unavailable", "Web search is unavailable for the moment.", 503)


class SearchNotServed(SearchUnavailable):
    """Same error for the caller, but the provider **neither served nor billed** the request:
    nothing left (invalid key, connection impossible) or it was refused outright (429
    rate limit, 401/403 key refused). A request reserved on a counter can be given back."""


class SearchProvider(Protocol):
    name: str

    async def search(
        self,
        query: str,
        *,
        lang: str | None = None,
        time_range: TimeRange | None = None,
        categories: Sequence[str] = (),
    ) -> list[SearchResult]:
        """At most `MAX_RESULTS` results, unique http(s) links. Raises `SearchUnavailable`."""
        ...


def is_web_url(url: object) -> bool:
    """http(s) link with a host: any other result (javascript:, ftp:, empty) is dropped."""
    if not isinstance(url, str):
        return False
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    return parts.scheme in ("http", "https") and bool(parts.hostname)


def text_or_empty(value: object) -> str:
    return value if isinstance(value, str) else ""


def keep_unique(results: list[SearchResult]) -> list[SearchResult]:
    """First result of each URL, `MAX_RESULTS` at most, in the order received."""
    seen: set[str] = set()
    unique: list[SearchResult] = []
    for result in results:
        if result.url in seen:
            continue
        seen.add(result.url)
        unique.append(result)
        if len(unique) == MAX_RESULTS:
            break
    return unique
