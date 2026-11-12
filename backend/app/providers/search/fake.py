"""Faux fournisseur de recherche : tests et contrôle de fin de phase, sans réseau."""

from collections.abc import Sequence
from dataclasses import dataclass, field

from app.core.errors import AppError
from app.providers.search.base import MAX_RESULTS, SearchResult, TimeRange


@dataclass
class FakeSearch:
    """`results` : requête → résultats (toute autre requête : aucun) ; `error` est levée à
    chaque appel s'il est posé ; `calls` garde (requête, langue) dans l'ordre."""

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
