"""Port de la recherche web (SPEC 10.1) : types partagés, limites et erreur unique.

Aucun message d'erreur ni journal ne cite la requête, une URL ou une clé (SPEC 17.2) : les
implémentations ne journalisent que leur nom, un statut HTTP ou un type d'exception."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol
from urllib.parse import urlsplit

from app.core.errors import AppError

TimeRange = Literal["day", "week", "month", "year"]
SEARCH_CATEGORIES = ("general", "it", "science", "videos")
MAX_RESULTS = 10
# Délai d'une recherche (SearXNG interroge ses moteurs en parallèle, Brave répond vite).
SEARCH_TIMEOUT_S = 10.0


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str
    engine: str
    published: str | None


class SearchUnavailable(AppError):
    """Fournisseur injoignable, en erreur ou sans moteur qui réponde : message fixe."""

    def __init__(self) -> None:
        super().__init__(
            "search_unavailable", "La recherche web est indisponible pour le moment.", 503
        )


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
        """`MAX_RESULTS` résultats au plus, liens http(s) uniques. Lève `SearchUnavailable`."""
        ...


def is_web_url(url: object) -> bool:
    """Lien http(s) avec un hôte : tout autre résultat (javascript:, ftp:, vide) est écarté."""
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
    """Premier résultat de chaque URL, `MAX_RESULTS` au plus, dans l'ordre reçu."""
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
