"""Recherche web (SPEC 10.1, 10.4, 11.3, 17.3) : requête nettoyée, cache de 24 h, ordre de repli
des fournisseurs, plafond de la session et plafond mensuel de Brave.

Aucune transaction n'est ouverte pendant un appel réseau (D66) : lecture (réglages, rejeu,
plafond, cache), puis appel, puis une écriture courte. Journaux : identifiants seulement, jamais
la requête (SPEC 17.2)."""

import logging
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.research import WebQuery
from app.features.auth.service import AuthService
from app.features.research.repository import WebQueryRepository
from app.features.research.service.cache import WebCache, search_key
from app.features.research.service.domains import RankedHit, rank_results
from app.features.research.service.errors import NoSearchProvider, WebQuotaReached, empty_query
from app.features.research.service.prefs import ResearchPrefs, load_prefs
from app.features.research.service.privacy import Identity, scrub_query
from app.features.research.service.runtime import ResearchRuntime
from app.features.research.service.usage import brave_key, reserve_brave
from app.providers.search.base import SearchProvider, SearchResult, SearchUnavailable, TimeRange

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchOutcome:
    query: str  # la requête nettoyée, celle qui a été envoyée
    provider: str | None
    hits: list[RankedHit]
    cached: bool
    replayed: bool


@dataclass(frozen=True)
class _Request:
    query: str
    lang: str | None
    time_range: TimeRange | None
    categories: tuple[str, ...]

    def cache_key(self, provider: str) -> str:
        return search_key(provider, self.query, self.lang, self.time_range, self.categories)

    @property
    def query_hash(self) -> str:
        """Identité de la requête dans la session, quel que soit le fournisseur qui a répondu."""
        return self.cache_key("query")


async def _load(runtime: ResearchRuntime, user_id: str) -> tuple[ResearchPrefs, Identity]:
    async with runtime.session_factory() as db:
        settings = await load_prefs(db, user_id)
        user = await AuthService(db).get_user(user_id)
    return settings, Identity(full_name=user.name or None, email=user.email)


async def _reserve_brave(
    runtime: ResearchRuntime, db: AsyncSession, user_id: str, api_key: str, now: datetime
) -> bool:
    """Sous `brave_lock`, une transaction à part, commitée avant l'appel : la requête du mois
    est réservée si la clé est sous 900 (contrôle et ajout indivisibles en SQL)."""
    async with runtime.brave_lock:
        return await reserve_brave(db, user_id, api_key, now)


async def _provider(
    runtime: ResearchRuntime, user_id: str, name: str, *, allow_brave: bool
) -> SearchProvider | None:
    if name == "searxng":
        return runtime.providers.searxng
    if name != "brave" or not allow_brave:
        return None
    api_key = await brave_key(runtime.keys, user_id)
    if api_key is None:
        return None
    async with runtime.session_factory() as db:
        reserved = await _reserve_brave(runtime, db, user_id, api_key, runtime.now())
    if not reserved:
        logger.info("Plafond mensuel de Brave atteint, Brave sauté (utilisateur %s)", user_id)
        return None
    return runtime.providers.brave(api_key)


async def _chain(
    runtime: ResearchRuntime,
    user_id: str,
    order: Sequence[str],
    request: _Request,
    *,
    allow_brave: bool,
) -> tuple[str, list[SearchResult]]:
    """Premier fournisseur de l'ordre qui rend au moins un résultat. Une panne ou une liste vide
    passe au suivant ; une chaîne épuisée lève `NoSearchProvider`."""
    for name in order:
        provider = await _provider(runtime, user_id, name, allow_brave=allow_brave)
        if provider is None:
            continue
        try:
            results = await provider.search(
                request.query,
                lang=request.lang,
                time_range=request.time_range,
                categories=request.categories,
            )
        except SearchUnavailable:
            logger.info("Fournisseur %s indisponible (utilisateur %s)", name, user_id)
            continue
        if results:
            return name, results
        logger.info("Fournisseur %s sans résultat (utilisateur %s)", name, user_id)
    raise NoSearchProvider()


async def _cached(
    runtime: ResearchRuntime, user_id: str, order: Sequence[str], request: _Request
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
    request: _Request,
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
    request: _Request,
    *,
    session_id: str | None,
    allow_brave: bool,
) -> SearchOutcome:
    order = settings.provider_order
    found = await _cached(runtime, user_id, order, request)
    cached = found is not None
    if found is None:
        found = await _chain(runtime, user_id, order, request, allow_brave=allow_brave)
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
    request: _Request,
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
) -> SearchOutcome:
    """Recherche `query` nettoyée de toute donnée personnelle. Lève `WebQuotaReached` (429),
    `NoSearchProvider` (503) ou 422 `search_query_empty`."""
    settings, identity = await _load(runtime, user_id)
    cleaned = scrub_query(query, identity)
    if not cleaned:
        raise empty_query()
    request = _Request(cleaned, lang, time_range, tuple(categories))
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
