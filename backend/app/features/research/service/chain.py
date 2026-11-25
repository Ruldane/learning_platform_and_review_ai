"""Fallback chain of the search providers (D76) and the Brave call: reservation on the monthly
cap, pace of one request per 1.1 s and per key, reservation given back when Brave neither
served nor billed the request (review of phase 3, I1).

No transaction or `brave_lock` is held while waiting for the slot or during the network call
(D66). Logs: ids only, never the query or the key (SPEC 17.2)."""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.research.service.cache import search_key
from app.features.research.service.errors import NoSearchProvider
from app.features.research.service.pacing import BRAVE_MAX_WAIT_S
from app.features.research.service.runtime import ResearchRuntime
from app.features.research.service.usage import (
    BraveReservation,
    brave_key,
    release_brave,
    reserve_brave,
)
from app.providers.search.base import (
    SearchNotServed,
    SearchProvider,
    SearchResult,
    SearchUnavailable,
    TimeRange,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchRequest:
    query: str
    lang: str | None
    time_range: TimeRange | None
    categories: tuple[str, ...]
    # Maximum wait accepted before the Brave call (pace); outside the cache key.
    budget_s: float = BRAVE_MAX_WAIT_S

    def cache_key(self, provider: str) -> str:
        return search_key(provider, self.query, self.lang, self.time_range, self.categories)

    @property
    def query_hash(self) -> str:
        """Identity of the request in the session, whichever provider answered."""
        return self.cache_key("query")


@dataclass(frozen=True)
class _Pick:
    provider: SearchProvider
    reservation: BraveReservation | None = None  # Brave seulement


async def _reserve_brave(
    runtime: ResearchRuntime, db: AsyncSession, user_id: str, api_key: str, now: datetime
) -> BraveReservation | None:
    """Under `brave_lock`, a separate transaction, committed before the call: the month's
    request is reserved if the key is under 900 (check and increment indivisible in SQL)."""
    async with runtime.brave_lock:
        return await reserve_brave(db, user_id, api_key, now)


async def _provider(
    runtime: ResearchRuntime, user_id: str, name: str, *, allow_brave: bool
) -> _Pick | None:
    if name == "searxng":
        return _Pick(runtime.providers.searxng)
    if name != "brave" or not allow_brave:
        return None
    api_key = await brave_key(runtime.keys, user_id)
    if api_key is None:
        return None
    async with runtime.session_factory() as db:
        reservation = await _reserve_brave(runtime, db, user_id, api_key, runtime.now())
    if reservation is None:
        logger.info("Brave monthly cap reached, Brave skipped (user %s)", user_id)
        return None
    return _Pick(runtime.providers.brave(api_key), reservation)


async def _release(runtime: ResearchRuntime, user_id: str, reservation: BraveReservation) -> None:
    """Gives the reservation back. A database error (busy, disk) is swallowed and logged by its
    type: the request stays counted (at worst one too many out of 900), but the chain moves on
    to the next provider instead of failing (D82)."""
    try:
        async with runtime.session_factory() as db:
            released = await release_brave(db, user_id, reservation)
    except (SQLAlchemyError, OSError) as exc:
        logger.warning(
            "Unserved Brave request, reservation not given back (user %s): %s",
            user_id,
            type(exc).__name__,
        )
        return
    logger.info("Unserved Brave request given back (user %s): %s", user_id, released)


async def _call(
    runtime: ResearchRuntime, user_id: str, pick: _Pick, request: SearchRequest
) -> list[SearchResult]:
    """Brave: the reservation is made (transaction closed, `brave_lock` released); we wait for the
    key's slot, within the caller's budget, then call. A request that Brave neither served nor
    billed (429, key refused, nothing sent, slot outside the budget) is given back."""
    try:
        reservation = pick.reservation
        if reservation is not None and not await runtime.brave_pacer.wait(
            reservation.fingerprint, budget_s=request.budget_s
        ):
            logger.info("Brave skipped: slot timed out (user %s)", user_id)
            raise SearchNotServed()
        return await pick.provider.search(
            request.query,
            lang=request.lang,
            time_range=request.time_range,
            categories=request.categories,
        )
    except SearchNotServed:
        if pick.reservation is not None:
            await _release(runtime, user_id, pick.reservation)
        raise  # telle quelle : `provider_chain` passe au fournisseur suivant


async def provider_chain(
    runtime: ResearchRuntime,
    user_id: str,
    order: Sequence[str],
    request: SearchRequest,
    *,
    allow_brave: bool,
) -> tuple[str, list[SearchResult]]:
    """First provider of the order that returns at least one result. A failure or an empty list
    moves on to the next; an exhausted chain raises `NoSearchProvider`."""
    for name in order:
        pick = await _provider(runtime, user_id, name, allow_brave=allow_brave)
        if pick is None:
            continue
        try:
            results = await _call(runtime, user_id, pick, request)
        except SearchUnavailable:
            logger.info("Fournisseur %s indisponible (utilisateur %s)", name, user_id)
            continue
        if results:
            return name, results
        logger.info("Provider %s without a result (user %s)", name, user_id)
    raise NoSearchProvider()
