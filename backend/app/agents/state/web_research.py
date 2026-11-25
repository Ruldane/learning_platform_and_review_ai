"""State of the `web_research` graph: from the question to the sources rated and kept in memory."""

from typing import Any, TypedDict


class WebResearchState(TypedDict, total=False):
    query: str
    urls: list[str]  # pages to read on top of the results (trial, check)
    queries: list[dict[str, Any]]  # `PlannedQuery.model_dump()`, cut at the cap
    hits: list[dict[str, Any]]  # {url, title, preferred}, preferred first
    pages: list[dict[str, Any]]  # readable pages to rate (text trimmed for rating)
    unreadable: int  # unreadable pages (already flagged by `source.found`)
    verdicts: list[dict[str, Any]]  # one entry per rated page
    remembered: int  # kept sources written to memory (nothing written if already there)
    summary: str
