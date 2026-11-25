"""Port for web search for the agents (D77). `app.agents` imports no feature
(contract 6): it describes here what it needs; the composition (`app.bootstrap.web_gateway`)
plugs in the `research` feature implementation, as for memory (`MemoryGateway`, D68).

Any text coming from the web (title, extract, page) is untrusted content: the tools
(`web_tools`) frame it with `untrusted()` before returning it to a model (17.4).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

from app.core.errors import AppError

# Error codes of the `research` feature that the engine recognizes (it does not import the
# feature); a gateway test checks that they are the feature's.
QUOTA_CODE = "web_quota_reached"
SEARCH_UNAVAILABLE_CODE = "search_unavailable"

# Scoring grid of a source's rating (SPEC 10.3): maximum points per criterion, 100 in total.
CRITERIA_MAX: dict[str, int] = {
    "authority": 30,
    "freshness": 20,
    "depth": 20,
    "author": 15,
    "pedagogy": 15,
}
KEEP_THRESHOLD = 60


@dataclass(frozen=True)
class WebHit:
    title: str
    url: str
    snippet: str
    engine: str
    published: str | None
    preferred: bool  # preferred domain in the settings


@dataclass(frozen=True)
class WebSearchResult:
    query: str  # the query CLEANED of any personal data, the one that was sent
    provider: str | None
    hits: list[WebHit]


@dataclass(frozen=True)
class SourceVerdictView:
    source_id: str
    score: int | None  # `None`: rating impossible to establish (invalid model output, timeout)
    verdict: Literal["kept", "rejected"]
    reason: str
    summary: str = ""  # summary of the rating, reused as is when the verdict is replayed (D82)


@dataclass(frozen=True)
class PageRead:
    # `None` for a page without a `sources` row: domain excluded in the settings,
    # jamais lue (D77).
    source_id: str | None
    url: str
    status: Literal["ok", "unreadable"]
    title: str | None
    text: str
    author: str | None
    date: str | None
    lang: str | None
    reason: str | None
    # Source already rated in the session (node replayed, second search): its verdict, that
    # `judge` re-emits without calling the model again (D82).
    verdict: SourceVerdictView | None = None


@dataclass(frozen=True)
class PersonFound:
    """A practitioner spotted by the Scout (SPEC 10.3): public professional information
    only. `url` is a read page or a result of the session, never an address written by
    the model; `where`: where they publish (domains)."""

    name: str
    role: str
    url: str
    where: tuple[str, ...]


@dataclass(frozen=True)
class WebLimits:
    languages: tuple[str, ...]
    preferred: tuple[str, ...]
    max_queries: int
    max_pages: int


class WebGateway(Protocol):
    async def search(
        self,
        user_id: str,
        session_id: str,
        query: str,
        *,
        lang: str | None = None,
        time_range: str | None = None,
        categories: Sequence[str] = (),
    ) -> WebSearchResult: ...

    async def read(self, user_id: str, session_id: str, url: str) -> PageRead: ...

    async def judge(
        self,
        user_id: str,
        session_id: str,
        source_id: str,
        *,
        criteria: dict[str, int] | None,
        reason: str,
        summary: str,
    ) -> SourceVerdictView:
        """Rating (sum of the bounded criteria) and verdict of a source. `criteria=None`: no
        rating could be established, the source is discarded without a rating, with `reason`."""
        ...

    async def verdicts(
        self, user_id: str, session_id: str, source_ids: Sequence[str]
    ) -> dict[str, SourceVerdictView]:
        """Verdicts already set on these session sources (the others are absent): a
        `judge` replayed after a stop does not call the model again (D82)."""
        ...

    async def add_person(self, user_id: str, session_id: str, person: PersonFound) -> str:
        """Records the practitioner in the session's sources (`kind` `person`); idempotent
        (same person, same address: same row). Returns the source's id."""
        ...

    async def people(self, user_id: str, session_id: str) -> list[tuple[str, PersonFound]]:
        """Practitioners already recorded for the session, `(source_id, person)` in recording
        order: `spot_people` replayed re-emits them without calling the model again (D84)."""
        ...

    async def limits(self, user_id: str) -> WebLimits: ...


def web_unavailable() -> AppError:
    return AppError("web_unavailable", "Web search is unavailable in this runtime.", 503)


class _NoWeb:
    """Engine default value (existing tests, starts without web search)."""

    async def search(
        self,
        user_id: str,
        session_id: str,
        query: str,
        *,
        lang: str | None = None,
        time_range: str | None = None,
        categories: Sequence[str] = (),
    ) -> WebSearchResult:
        raise web_unavailable()

    async def read(self, user_id: str, session_id: str, url: str) -> PageRead:
        raise web_unavailable()

    async def judge(
        self,
        user_id: str,
        session_id: str,
        source_id: str,
        *,
        criteria: dict[str, int] | None,
        reason: str,
        summary: str,
    ) -> SourceVerdictView:
        raise web_unavailable()

    async def verdicts(
        self, user_id: str, session_id: str, source_ids: Sequence[str]
    ) -> dict[str, SourceVerdictView]:
        raise web_unavailable()

    async def add_person(self, user_id: str, session_id: str, person: PersonFound) -> str:
        raise web_unavailable()

    async def people(self, user_id: str, session_id: str) -> list[tuple[str, PersonFound]]:
        raise web_unavailable()

    async def limits(self, user_id: str) -> WebLimits:
        raise web_unavailable()


NO_WEB: WebGateway = _NoWeb()
