"""Recherche web (SPEC 10.1, 10.4, 11.3, 17.3) : requête nettoyée, cache de 24 h, ordre de repli
des fournisseurs, plafond de la session et plafond mensuel de Brave.

Aucune transaction n'est ouverte pendant un appel réseau (D66) : lecture (réglages, rejeu,
plafond, cache), puis appel, puis une écriture courte. Journaux : identifiants seulement, jamais
la requête (SPEC 17.2)."""

import logging
from collections.abc import Sequence
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


@dataclass(frozen=True)
class SearchOutcome:
    query: str  # la requête nettoyée, celle qui a été envoyée
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
    """Liste encore en cache (24 h), cherchée fournisseur par fournisseur dans l'ordre."""
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
    """Une seule transaction courte : liste mise en cache (jamais vide : une liste vide n'arrive
    pas jusqu'ici), requête de la session, purge du cache si due."""
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
) -> SearchOutcome:
    order = settings.provider_order
    found = await _cached(runtime, user_id, order, request)
    cached = found is not None
    if found is None:
        found = await provider_chain(runtime, user_id, order, request, allow_brave=allow_brave)
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
) -> SearchOutcome:
    """À appeler sous `session_lock`. Une requête déjà lancée par la session (nœud rejoué) n'est
    ni recomptée ni refacturée : liste du cache, sinon nouvel essai sans Brave."""
    async with runtime.session_factory() as db:
        repo = WebQueryRepository(db, user_id)
        known = await repo.get(session_id, request.query_hash)
        count = await repo.count(session_id) if known is None else 0
    if known is not None:
        outcome = await _run(
            runtime, user_id, settings, request, session_id=None, allow_brave=False
        )
        return replace(outcome, replayed=True)
    if count >= settings.max_queries:
        raise WebQuotaReached(settings.max_queries, "queries")
    return await _run(runtime, user_id, settings, request, session_id=session_id, allow_brave=True)


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
) -> SearchOutcome:
    """Recherche `query` nettoyée de toute donnée personnelle. `budget_s` : attente maximale
    acceptée pour le créneau de Brave (au-delà, Brave est sauté). Lève `WebQuotaReached` (429),
    `NoSearchProvider` (503) ou 422 `search_query_empty`."""
    settings, identity = await _load(runtime, user_id)
    cleaned = scrub_query(query, identity)
    if not cleaned:
        raise empty_query()
    request = SearchRequest(cleaned, lang, time_range, tuple(categories), budget_s)
    try:
        if session_id is None:
            outcome = await _run(
                runtime, user_id, settings, request, session_id=None, allow_brave=True
            )
        else:
            async with runtime.session_lock(user_id, session_id):
                outcome = await _in_session(runtime, user_id, session_id, settings, request)
    except (NoSearchProvider, WebQuotaReached) as exc:
        logger.warning(
            "Recherche web : utilisateur %s, session %s, %s", user_id, session_id, exc.code
        )
        raise
    logger.info(
        "Recherche web : utilisateur %s, session %s, fournisseur %s, %d résultat(s), "
        "cache %s, rejouée %s",
        user_id,
        session_id,
        outcome.provider,
        len(outcome.hits),
        outcome.cached,
        outcome.replayed,
    )
    return outcome
