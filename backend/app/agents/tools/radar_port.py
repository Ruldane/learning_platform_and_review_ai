"""Port for the market radar (P5, P6, D159). `app.agents` imports no feature (contract 6): it
describes here what the `market_radar` graph needs; the `radar` feature implements it
(`AgentRadarStore`, task 8.4).

The links, pages and extractions are the user's or the web's data (17.2, 17.4):
never logged, neither here nor by the implementation. Every write is **idempotent** (SPEC 9.4):
a node replayed after a stop writes, rereads and recounts nothing more.

- `context`: read-only; the survey's state as it is in the database (pages read, offers extracted,
  reads done). The read loop and the extraction loop reread it on every pass.
- `read_posting`: reads the page (the engine's web reader, outside the session page cap: its own
  budget of `MAX_READS`) and stores it; idempotent per (survey, link normalized by
  `posting_url_key`): an already read page is returned without rereading or recounting. A page that
  cannot be read (blocked site, refused link) is not an error: `status = "unreadable"`.
- `save_extraction`: the extracted offers (`RadarFinding`), `ref` = `PostingPage.ref`;
  `failed_refs`: the pages
  whose extraction failed (counted as extracted so they are not taken again). Idempotent per
  `ref`.
- `finalize`: computes the report (real numbers: read, blocked, not offers, analyzed).
- `fail`: the survey fails with this code (`search_unavailable`...), with nothing else."""

from dataclasses import dataclass, field
from typing import Literal, Protocol

from app.agents.tools.radar_schema import RadarFinding
from app.core.errors import AppError

# Bounds of P5, copied from `radar.service.rules` (the engine does not import the feature): a test
# checks that they are the same.
MAX_CANDIDATES = 80  # links kept after the search
MAX_READS = 60  # reads at most per survey
MAX_READABLE = 50  # reading stops at 50 readable offers, and no extraction beyond


@dataclass(frozen=True)
class PostingPage:
    """A page read. `ref`: its stable mark in the survey; `url`: the link as given to
    `read_posting`; `domain`: its site (counted separately when it blocks); `text`: empty if
    `unreadable`."""

    ref: str
    url: str
    domain: str
    status: Literal["ok", "unreadable"]
    text: str


@dataclass(frozen=True)
class RadarContext:
    run_id: str
    role: str
    zone: str
    languages: tuple[str, ...]
    read: list[PostingPage] = field(default_factory=list)  # pages already read, in reading order
    extracted: frozenset[str] = frozenset()  # refs already extracted (or failed extraction)
    attempts: int = 0  # reads already done (≤ MAX_READS)


@dataclass(frozen=True)
class RadarSummary:
    """The survey report: `read_ok` readable pages (including `not_postings`, which are not
    offers), `blocked` unreadable pages, `analyzed` analyzed offers, `low_sample`: fewer than 30
    readable offers. `error_code`: `analysis_failed` if no offer could be analyzed for lack
    of extraction (the survey is then `failed`, never "finished" empty); otherwise `None`."""

    read_ok: int
    blocked: int
    not_postings: int
    analyzed: int
    low_sample: bool
    error_code: str | None = None


class RadarStore(Protocol):
    async def context(self, user_id: str, run_id: str) -> RadarContext: ...

    async def save_candidates(
        self, user_id: str, session_id: str, run_id: str, queries: int, urls: list[str]
    ) -> None: ...

    async def read_posting(
        self, user_id: str, session_id: str, run_id: str, url: str
    ) -> PostingPage: ...

    async def save_extraction(
        self,
        user_id: str,
        session_id: str,
        run_id: str,
        items: list[RadarFinding],
        failed_refs: list[str],
    ) -> None: ...

    async def finalize(self, user_id: str, session_id: str, run_id: str) -> RadarSummary: ...

    async def fail(self, user_id: str, session_id: str, run_id: str, code: str) -> None: ...


def radar_unavailable() -> AppError:
    return AppError("radar_unavailable", "Market Radar is unavailable in this runtime.", 503)


class _NoRadar:
    """Engine default value (tests, starts without the feature)."""

    async def context(self, user_id: str, run_id: str) -> RadarContext:
        raise radar_unavailable()

    async def save_candidates(
        self, user_id: str, session_id: str, run_id: str, queries: int, urls: list[str]
    ) -> None:
        raise radar_unavailable()

    async def read_posting(
        self, user_id: str, session_id: str, run_id: str, url: str
    ) -> PostingPage:
        raise radar_unavailable()

    async def save_extraction(
        self,
        user_id: str,
        session_id: str,
        run_id: str,
        items: list[RadarFinding],
        failed_refs: list[str],
    ) -> None:
        raise radar_unavailable()

    async def finalize(self, user_id: str, session_id: str, run_id: str) -> RadarSummary:
        raise radar_unavailable()

    async def fail(self, user_id: str, session_id: str, run_id: str, code: str) -> None:
        raise radar_unavailable()


NO_RADAR: RadarStore = _NoRadar()
