"""The offers examined in a scan (`postings` column, D157): entry shape, reading an entry as a
port page, and counts. Pure rules, without database; `text` (4,000 characters at most) lives
only as long as the scan: `finalize` removes it."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from app.agents.tools.radar_port import PostingPage

Entry = dict[str, Any]


@dataclass(frozen=True)
class Counts:
    """The real numbers of a scan: readable pages, blocked ones, those that were not offers,
    analysed offers."""

    read: int
    blocked: int
    not_postings: int
    analyzed: int


def domain_of(url: str) -> str:
    """The site of a link (lowercase, without `www.`), empty if the link has none."""
    try:
        host = urlsplit(url.strip()).hostname or ""
    except ValueError:
        return ""
    return host.lower().removeprefix("www.")


def is_analyzed(entry: Entry) -> bool:
    return entry.get("read") == "ok" and isinstance(entry.get("skills"), list)


def is_extracted(entry: Entry) -> bool:
    """An offer that has its outcome: analysed, not an offer, or extraction failed."""
    return entry.get("read") in ("not_posting", "extract_failed") or is_analyzed(entry)


def is_closed(entry: Entry) -> bool:
    """Nothing left to extract: blocked page, or outcome already stored."""
    return entry.get("read") == "blocked" or is_extracted(entry)


def page_of(entry: Entry) -> PostingPage:
    """The entry as the path sees it: an `ok` page (readable, even if it is not an offer) or
    `unreadable` (blocked)."""
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
    """No offer analysed although the extraction failed on at least one: the scan is failed (a retry
    is possible), never "finished" with zero offers analysed."""
    return not any(is_analyzed(entry) for entry in entries) and any(
        entry.get("read") == "extract_failed" for entry in entries
    )


def blocked_domains(entries: Sequence[Entry]) -> dict[str, int]:
    """`site → number of blocked pages`, in the order of first encounter."""
    found: dict[str, int] = {}
    for entry in entries:
        if entry.get("read") == "blocked":
            domain = str(entry.get("domain", ""))
            found[domain] = found.get(domain, 0) + 1
    return found
