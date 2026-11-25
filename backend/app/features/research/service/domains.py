from collections.abc import Sequence
from dataclasses import dataclass
from urllib.parse import urlsplit

from app.core.domains import normalize_domain
from app.providers.search.base import SearchResult

__all__ = ["RankedHit", "host_matches", "normalize_domain", "rank_results"]


def host_matches(host: str, domain: str) -> bool:
    """`host` is `domain` or one of its subdomains (`docs.python.org` ⊂ `python.org`)."""
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
            continue  # an invalid entry neither removes nor favours anything
    return cleaned


def _host(url: str) -> str:
    try:
        return urlsplit(url).hostname or ""
    except ValueError:
        return ""


def rank_results(
    results: Sequence[SearchResult], *, preferred: Sequence[str], excluded: Sequence[str]
) -> list[RankedHit]:
    """Removes excluded domains (subdomains included: exclusion beats preference), then moves the
    preferred ones to the front; the original order is kept within each group."""
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
