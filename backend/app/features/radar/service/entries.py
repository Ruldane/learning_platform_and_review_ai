"""Les offres examinées d'un relevé (colonne `postings`, D157) : forme des entrées, lecture d'une
entrée comme page du port et comptes. Règles pures, sans base ; `text` (4 000 caractères au plus)
ne vit que le temps du relevé : `finalize` le retire."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from app.agents.tools.radar_port import PostingPage

Entry = dict[str, Any]


@dataclass(frozen=True)
class Counts:
    """Les nombres réels d'un relevé : pages lisibles, bloquées, qui n'étaient pas des offres,
    offres analysées."""

    read: int
    blocked: int
    not_postings: int
    analyzed: int


def domain_of(url: str) -> str:
    """Le site d'un lien (minuscules, sans `www.`), vide si le lien n'en a pas."""
    try:
        host = urlsplit(url.strip()).hostname or ""
    except ValueError:
        return ""
    return host.lower().removeprefix("www.")


def is_analyzed(entry: Entry) -> bool:
    return entry.get("read") == "ok" and isinstance(entry.get("skills"), list)


def is_extracted(entry: Entry) -> bool:
    """Une offre qui a son issue : analysée, pas une offre, ou extraction en échec."""
    return entry.get("read") in ("not_posting", "extract_failed") or is_analyzed(entry)


def is_closed(entry: Entry) -> bool:
    """Plus rien à extraire : page bloquée, ou issue déjà rangée."""
    return entry.get("read") == "blocked" or is_extracted(entry)


def page_of(entry: Entry) -> PostingPage:
    """L'entrée vue par le parcours : une page `ok` (lisible, même si ce n'est pas une offre) ou
    `unreadable` (bloquée)."""
    blocked = entry.get("read") == "blocked"
    return PostingPage(
        ref=str(entry["ref"]),
        url=str(entry["url"]),
        domain=str(entry.get("domain", "")),
        status="unreadable" if blocked else "ok",
        text="" if blocked else str(entry.get("text", "")),
    )


def count(entries: Sequence[Entry]) -> Counts:
    blocked = sum(entry.get("read") == "blocked" for entry in entries)
    return Counts(
        read=len(entries) - blocked,
        blocked=blocked,
        not_postings=sum(entry.get("read") == "not_posting" for entry in entries),
        analyzed=sum(is_analyzed(entry) for entry in entries),
    )


def analysis_failed(entries: Sequence[Entry]) -> bool:
    """Aucune offre analysée alors que l'extraction a échoué sur au moins une : le relevé est en
    échec (reprise possible), jamais « terminé » avec zéro offre analysée."""
    return not any(is_analyzed(entry) for entry in entries) and any(
        entry.get("read") == "extract_failed" for entry in entries
    )


def blocked_domains(entries: Sequence[Entry]) -> dict[str, int]:
    """`site → nombre de pages bloquées`, dans l'ordre de la première rencontre."""
    found: dict[str, int] = {}
    for entry in entries:
        if entry.get("read") == "blocked":
            domain = str(entry.get("domain", ""))
            found[domain] = found.get(domain, 0) + 1
    return found
