from collections.abc import Sequence
from dataclasses import dataclass
from urllib.parse import urlsplit

from app.core.domains import normalize_domain
from app.providers.search.base import SearchResult

__all__ = ["RankedHit", "host_matches", "normalize_domain", "rank_results"]


def host_matches(host: str, domain: str) -> bool:
    """`host` est `domain` ou l'un de ses sous-domaines (`docs.python.org` ⊂ `python.org`)."""
    host = host.lower().rstrip(".")
    domain = domain.lower().rstrip(".")
    return bool(domain) and (host == domain or host.endswith(f".{domain}"))


@dataclass(frozen=True)
class RankedHit:
    result: SearchResult
    preferred: bool


def _clean(domains: Sequence[str]) -> list[str]:
    cleaned: list[str] = []
    for domain in domains:
        try:
            cleaned.append(normalize_domain(domain))
        except ValueError:
            continue  # une saisie invalide ne retire ni ne privilégie rien
    return cleaned


def _host(url: str) -> str:
    try:
        return urlsplit(url).hostname or ""
    except ValueError:
        return ""


def rank_results(
    results: Sequence[SearchResult], *, preferred: Sequence[str], excluded: Sequence[str]
) -> list[RankedHit]:
    """Retire les domaines exclus (sous-domaines compris, l'exclusion l'emporte sur la préférence),
    puis met les privilégiés en tête ; l'ordre d'origine est conservé dans chaque groupe."""
    keep, drop = _clean(preferred), _clean(excluded)
    first: list[RankedHit] = []
    rest: list[RankedHit] = []
    for result in results:
        host = _host(result.url)
        if any(host_matches(host, domain) for domain in drop):
            continue
        is_preferred = any(host_matches(host, domain) for domain in keep)
        (first if is_preferred else rest).append(RankedHit(result, is_preferred))
    return first + rest
