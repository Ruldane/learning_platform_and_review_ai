"""Web search (SPEC 10.1, 10.4, 11.3, 17.3): cleaned query, 24 h cache, provider fallback
order, session cap and Brave monthly cap.

No transaction is open during a network call (D66): read (settings, replay, cap, cache), then
call, then a short write. Logs: ids only, never the query (SPEC 17.2)."""

import logging
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, replace

from app.db.models.research import WebQuery
from app.features.auth.service import AuthService
from app.features.research.repository import WebQueryRepository
from app.features.research.service.cache import WebCache
from app.features.research.service.chain import SearchRequest, provider_chain
from app.features.research.service.domains import RankedHit, rank_results
from app.features.research.service.errors import NoSearchProvider, WebQuotaReached, empty_query
from app.features.research.service.pacing import BRAVE_MAX_WAIT_S
from app.features.research.service.prefs import ResearchPrefs, load_prefs
from app.features.research.service.privacy import Identity, scrub_query
from app.features.research.service.runtime import ResearchRuntime
from app.providers.search.base import SearchResult, TimeRange

logger = logging.getLogger(__name__)
type SearchFromClient = Callable[[SearchRequest, ResearchPrefs], Awaitable[list[SearchResult]]]


@dataclass(frozen=True)
class SearchOutcome:
    query: str  # the cleaned query, the one that was sent
    provider: str | None
    hits: list[RankedHit]
    cached: bool
    replayed: bool


async def _load(runtime: ResearchRuntime, user_id: str) -> tuple[ResearchPrefs, Identity]:
    async with runtime.session_factory() as db:
        settings = await load_prefs(db, user_id)
        user = await AuthService(db).get_user(user_id)
    return settings, Identity(full_name=user.name or None, email=user.email)


async def _cached(
    runtime: ResearchRuntime, user_id: str, order: Sequence[str], request: SearchRequest
) -> tuple[str, list[SearchResult]] | None:
    """List still cached (24 h), searched provider by provider in order."""
    async with runtime.session_factory() as db:
        cache = WebCache(db, user_id, now=runtime.now)
        for name in order:
            results = await cache.get_search(request.cache_key(name))
            if results:
                return name, results
    return None


async def _save(
    runtime: ResearchRuntime,
    user_id: str,
    request: SearchRequest,
    found: tuple[str, list[SearchResult]],
    *,
    store: bool,
    session_id: str | None,
    hit_count: int,
) -> None:
    """A single short transaction: list cached (never empty: an empty list does not get here),
    the session's query, cache purge if due."""
    provider, results = found
    async with runtime.session_factory() as db:
        if store:
            await WebCache(db, user_id, now=runtime.now).put_search(
                request.cache_key(provider), results
            )
        if session_id is not None:
            query = WebQuery(
                session_id=session_id,
                query_hash=request.query_hash,
                query=request.query,
                lang=request.lang,
                provider=provider,
                result_count=hit_count,
            )
            await WebQueryRepository(db, user_id).add(query)
        await runtime.purge_if_due(db, user_id)
        await db.commit()


async def _run(
    runtime: ResearchRuntime,
    user_id: str,
    settings: ResearchPrefs,
    request: SearchRequest,
    *,
    session_id: str | None,
    allow_brave: bool,
    client: SearchFromClient | None = None,
) -> SearchOutcome:
    order = ("mcp",) if client is not None else settings.provider_order
    found = await _cached(runtime, user_id, order, request)
    cached = found is not None
    if found is None:
        found = (
            ("mcp", await client(request, settings))
            if client is not None
            else await provider_chain(runtime, user_id, order, request, allow_brave=allow_brave)
        )
    hits = rank_results(found[1], preferred=settings.preferred, excluded=settings.excluded)
    await _save(
        runtime,
        user_id,
        request,
        found,
        store=not cached,
        session_id=session_id,
        hit_count=len(hits),
    )
    return SearchOutcome(request.query, found[0], hits, cached=cached, replayed=False)


async def _in_session(
    runtime: ResearchRuntime,
    user_id: str,
    session_id: str,
    settings: ResearchPrefs,
    request: SearchRequest,
    client: SearchFromClient | None = None,
) -> SearchOutcome:
    """To call under `session_lock`. A query already launched by the session (replayed node) is
    neither recounted nor rebilled: list from the cache, otherwise a new try without Brave."""
    async with runtime.session_factory() as db:
        repo = WebQueryRepository(db, user_id)
        known = await repo.get(session_id, request.query_hash)
        count = await repo.count(session_id) if known is None else 0
    if known is not None:
        outcome = await _run(
            runtime,
            user_id,
            settings,
            request,
            session_id=None,
            allow_brave=False,
            client=client,
        )
        return replace(outcome, replayed=True)
    if count >= settings.max_queries:
        raise WebQuotaReached(settings.max_queries, "queries")
    return await _run(
        runtime,
        user_id,
        settings,
        request,
        session_id=session_id,
        allow_brave=True,
        client=client,
    )


async def search(
    runtime: ResearchRuntime,
    user_id: str,
    session_id: str | None,
    query: str,
    *,
    lang: str | None = None,
    time_range: TimeRange | None = None,
    categories: Sequence[str] = (),
    budget_s: float = BRAVE_MAX_WAIT_S,
    client: SearchFromClient | None = None,
) -> SearchOutcome:
    """Searches `query` cleaned of any personal data. `budget_s`: maximum wait accepted for
    Brave's slot (beyond it, Brave is skipped). Raises `WebQuotaReached` (429),
    `NoSearchProvider` (503) or 422 `search_query_empty`."""
    settings, identity = await _load(runtime, user_id)
    cleaned = scrub_query(query, identity)
    if not cleaned:
        raise empty_query()
    request = SearchRequest(cleaned, lang, time_range, tuple(categories), budget_s)
    try:
        if session_id is None:
            outcome = await _run(
                runtime,
                user_id,
                settings,
                request,
                session_id=None,
                allow_brave=True,
                client=client,
            )
        else:
            async with runtime.session_lock(user_id, session_id):
                outcome = await _in_session(runtime, user_id, session_id, settings, request, client)
    except (NoSearchProvider, WebQuotaReached) as exc:
        logger.warning(
            "Recherche web : utilisateur %s, session %s, %s", user_id, session_id, exc.code
        )
        raise
    logger.info(
        "Web search: user %s, session %s, provider %s, %d result(s), cache %s, replayed %s",
        user_id,
        session_id,
        outcome.provider,
        len(outcome.hits),
        outcome.cached,
        outcome.replayed,
    )
    return outcome
