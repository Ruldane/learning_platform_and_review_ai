"""Agents' web gateway (D77): implements the `WebGateway` port of `app.agents` on the research
service. Each call opens its own short database sessions (D66); a session's search and read
go under its lock (`searching`, `reading`), so a replayed node recounts nothing and duplicates
no source.

Logs: ids only, never a query, a URL or a title (SPEC 17.2)."""

import logging
from collections.abc import Sequence
from typing import get_args

from app.agents.tools.web_port import (
    CRITERIA_MAX,
    PageRead,
    PersonFound,
    SourceVerdictView,
    WebHit,
    WebLimits,
    WebSearchResult,
)
from app.core.played import played_by
from app.db.models.research import PageStatus
from app.features.research.service.client_web import ClientWeb
from app.features.research.service.people import person_of, record_person, session_people
from app.features.research.service.prefs import load_prefs
from app.features.research.service.reading import (
    Judged,
    PageOutcome,
    read,
    record_verdict,
    session_verdicts,
)
from app.features.research.service.runtime import ResearchRuntime
from app.features.research.service.searching import SearchOutcome, search
from app.providers.search.base import TimeRange

logger = logging.getLogger(__name__)

_TIME_RANGES: tuple[str, ...] = get_args(TimeRange)


def _time_range(value: str | None) -> TimeRange | None:
    """An unknown period is ignored (the model may invent one) rather than refused."""
    return value if value in _TIME_RANGES else None  # type: ignore[return-value]


def _search_result(outcome: SearchOutcome) -> WebSearchResult:
    hits = [
        WebHit(
            title=ranked.result.title,
            url=ranked.result.url,
            snippet=ranked.result.snippet,
            engine=ranked.result.engine,
            published=ranked.result.published,
            preferred=ranked.preferred,
        )
        for ranked in outcome.hits
    ]
    return WebSearchResult(query=outcome.query, provider=outcome.provider, hits=hits)


def _view(source_id: str, judged: Judged) -> SourceVerdictView:
    return SourceVerdictView(
        source_id=source_id,
        score=judged.score,
        verdict=judged.verdict,
        reason=judged.reason,
        summary=judged.summary,
    )


def _verdict(outcome: PageOutcome) -> SourceVerdictView | None:
    """Verdict already set in the session (D82): `judge` re-emits it without calling the model."""
    judged = outcome.judged
    if judged is None or outcome.source_id is None:
        return None
    return _view(outcome.source_id, judged)


def _page(outcome: PageOutcome) -> PageRead:
    status: PageStatus = outcome.status
    return PageRead(
        source_id=outcome.source_id,
        url=outcome.url,
        status=status,
        title=outcome.title,
        text=outcome.text,
        author=outcome.author,
        date=outcome.date,
        lang=outcome.lang,
        reason=outcome.reason,
        verdict=_verdict(outcome),
    )


def _detail(criteria: dict[str, int]) -> dict[str, int]:
    """Points per criterion, each bounded to its scale (10.3); an unknown key does not count.
    The score out of 100 is the sum: the model never gives the total."""
    return {
        name: max(0, min(maximum, criteria.get(name, 0))) for name, maximum in CRITERIA_MAX.items()
    }


class AgentWebGateway:
    def __init__(self, runtime: ResearchRuntime) -> None:
        self._runtime = runtime

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
        client = played_by(user_id)
        outcome = await search(
            self._runtime,
            user_id,
            session_id,
            query,
            lang=lang,
            time_range=_time_range(time_range),
            categories=categories,
            client=ClientWeb(user_id, client).search if client else None,
        )
        return _search_result(outcome)

    async def read(self, user_id: str, session_id: str, url: str) -> PageRead:
        client = played_by(user_id)
        fetch = ClientWeb(user_id, client).read if client else None
        return _page(await read(self._runtime, user_id, session_id, url, client=fetch))

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
        """Records the score and the verdict (idempotent: a replayed node writes the same thing).
        `criteria=None`: discarded without a score (score impossible to establish).
        `source_not_found` (404) if the source is not the user's."""
        detail = None if criteria is None else _detail(criteria)
        async with self._runtime.session_factory() as db:
            source = await record_verdict(
                db,
                user_id,
                source_id,
                score=None if detail is None else sum(detail.values()),
                detail=detail,
                reason=reason,
                summary=summary,
            )
            await db.commit()
            view = SourceVerdictView(
                source_id=source.id,
                score=source.score,
                verdict="kept" if source.verdict == "kept" else "rejected",
                reason=source.reason or "",
                summary=source.summary or "",
            )
        logger.info(
            "Source scored: user %s, session %s, source %s, %s",
            user_id,
            session_id,
            source_id,
            view.verdict,
        )
        return view

    async def verdicts(
        self, user_id: str, session_id: str, source_ids: Sequence[str]
    ) -> dict[str, SourceVerdictView]:
        """Verdicts already set (filtered by user and session) among `source_ids`."""
        wanted = set(source_ids)
        if not wanted:
            return {}
        async with self._runtime.session_factory() as db:
            known = await session_verdicts(db, user_id, session_id)
        return {sid: _view(sid, judged) for sid, judged in known.items() if sid in wanted}

    async def add_person(self, user_id: str, session_id: str, person: PersonFound) -> str:
        """Practitioner recorded in the session's sources (idempotent), under the session lock
        like a read: two writes of the same person make only one."""
        lock = self._runtime.session_lock(user_id, session_id)
        async with lock, self._runtime.session_factory() as db:
            source = await record_person(db, user_id, session_id, person)
            await db.commit()
            return source.id

    async def people(self, user_id: str, session_id: str) -> list[tuple[str, PersonFound]]:
        """Practitioners already recorded (filtered by user and session)."""
        async with self._runtime.session_factory() as db:
            rows = await session_people(db, user_id, session_id)
        return [(row.id, person_of(row)) for row in rows]

    async def limits(self, user_id: str) -> WebLimits:
        async with self._runtime.session_factory() as db:
            prefs = await load_prefs(db, user_id)
        return WebLimits(
            languages=prefs.languages,
            preferred=prefs.preferred,
            max_queries=prefs.max_queries,
            max_pages=prefs.max_pages,
        )
