import re
from collections.abc import Sequence
from dataclasses import dataclass
from urllib.parse import urlsplit

from app.providers.search.base import SearchResult

# Même règle que `normalizeDomain.ts` du front (réglages de recherche) : les deux doivent accepter
# et refuser exactement les mêmes saisies. `[0-9]` et `fullmatch` pour ne pas dépendre de `\d`
# (chiffres Unicode) ni de `$` (qui tolère un saut de ligne final).
_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*://")
_LABEL = re.compile(r"[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?")
_TLD = re.compile(r"[a-z]{2,63}|xn--[a-z0-9-]{1,59}")
_PORT = re.compile(r":[0-9]*\Z")
_MAX_HOST = 253


def normalize_domain(value: str) -> str:
    """Ramène une saisie à un nom de domaine : minuscules, sans schéma, identifiants, chemin,
    requête, fragment, port, point final ni « www. ». Lève `ValueError` si ce n'est pas un
    domaine : au moins deux étiquettes, extension alphabétique (adresses IP et « localhost »
    refusées)."""
    host = _SCHEME.sub("", value.strip().lower(), count=1)
    host = re.split(r"[/?#]", host, maxsplit=1)[0]
    host = host[host.rfind("@") + 1 :]
    host = _PORT.sub("", host, count=1)
    host = host.removesuffix(".")
    host = host.removeprefix("www.")
    labels = host.split(".")
    if not 0 < len(host) <= _MAX_HOST or len(labels) < 2:
        raise ValueError("domaine invalide")
    if not all(_LABEL.fullmatch(label) for label in labels):
        raise ValueError("domaine invalide")
    if not _TLD.fullmatch(labels[-1]):
        raise ValueError("domaine invalide")
    return host


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
