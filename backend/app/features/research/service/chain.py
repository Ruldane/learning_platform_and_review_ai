"""Chaîne de repli des fournisseurs de recherche (D76) et appel à Brave : réservation sur le
plafond mensuel, cadence d'une requête par 1,1 s et par clé, réservation rendue quand Brave n'a
ni servi ni facturé la requête (revue de la phase 3, I1).

Aucune transaction ni `brave_lock` n'est tenu pendant l'attente du créneau ou l'appel réseau
(D66). Journaux : identifiants seulement, jamais la requête ni la clé (SPEC 17.2)."""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

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
    # Attente maximale acceptée avant l'appel à Brave (cadence) ; hors clé de cache.
    budget_s: float = BRAVE_MAX_WAIT_S

    def cache_key(self, provider: str) -> str:
        return search_key(provider, self.query, self.lang, self.time_range, self.categories)

    @property
    def query_hash(self) -> str:
        """Identité de la requête dans la session, quel que soit le fournisseur qui a répondu."""
        return self.cache_key("query")


@dataclass(frozen=True)
class _Pick:
    provider: SearchProvider
    reservation: BraveReservation | None = None  # Brave seulement


async def _reserve_brave(
    runtime: ResearchRuntime, db: AsyncSession, user_id: str, api_key: str, now: datetime
) -> BraveReservation | None:
    """Sous `brave_lock`, une transaction à part, commitée avant l'appel : la requête du mois
    est réservée si la clé est sous 900 (contrôle et ajout indivisibles en SQL)."""
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
        logger.info("Plafond mensuel de Brave atteint, Brave sauté (utilisateur %s)", user_id)
        return None
    return _Pick(runtime.providers.brave(api_key), reservation)


async def _release(runtime: ResearchRuntime, user_id: str, reservation: BraveReservation) -> None:
    async with runtime.session_factory() as db:
        released = await release_brave(db, user_id, reservation)
    logger.info("Requête Brave non servie rendue (utilisateur %s) : %s", user_id, released)


async def _call(
    runtime: ResearchRuntime, user_id: str, pick: _Pick, request: SearchRequest
) -> list[SearchResult]:
    """Brave : la réservation est faite (transaction close, `brave_lock` rendu) ; on attend le
    créneau de la clé, dans le budget de l'appelant, puis on appelle. Une requête que Brave n'a
    ni servie ni facturée (429, clé refusée, rien d'envoyé, créneau hors budget) est rendue."""
    try:
        reservation = pick.reservation
        if reservation is not None and not await runtime.brave_pacer.wait(
            reservation.fingerprint, budget_s=request.budget_s
        ):
            logger.info("Brave sauté : créneau hors délai (utilisateur %s)", user_id)
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
        raise


async def provider_chain(
    runtime: ResearchRuntime,
    user_id: str,
    order: Sequence[str],
    request: SearchRequest,
    *,
    allow_brave: bool,
) -> tuple[str, list[SearchResult]]:
    """Premier fournisseur de l'ordre qui rend au moins un résultat. Une panne ou une liste vide
    passe au suivant ; une chaîne épuisée lève `NoSearchProvider`."""
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
        logger.info("Fournisseur %s sans résultat (utilisateur %s)", name, user_id)
    raise NoSearchProvider()
