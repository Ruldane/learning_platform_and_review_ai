"""Fake search provider: tests and end-of-phase checks, no network."""

from collections.abc import Sequence
from dataclasses import dataclass, field

from app.core.errors import AppError
from app.providers.search.base import MAX_RESULTS, SearchResult, TimeRange


@dataclass
class FakeSearch:
    """`results`: query -> results (any other query: none); `error` is raised on each call if it is
    set; `calls` keeps (query, language) in order."""

    name: str
    results: dict[str, list[SearchResult]] = field(default_factory=dict)
    error: AppError | None = None
    calls: list[tuple[str, str | None]] = field(default_factory=list)

    async def search(
        self,
        query: str,
        *,
        lang: str | None = None,
        time_range: TimeRange | None = None,
        categories: Sequence[str] = (),
    ) -> list[SearchResult]:
        self.calls.append((query, lang))
        if self.error is not None:
            raise self.error
        return list(self.results.get(query, []))[:MAX_RESULTS]
