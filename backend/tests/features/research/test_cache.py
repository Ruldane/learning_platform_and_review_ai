from datetime import timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import AppError
from app.db.models.research import WebCacheEntry
from app.features.research.repository import WebCacheRepository
from app.features.research.service.cache import (
    SEARCH_TTL,
    CachedPage,
    WebCache,
    search_key,
    url_key,
)
from app.providers.search.base import SearchResult
from tests.features.research.conftest import Clock

OK_PAGE = CachedPage("ok", "T", "texte", None, None, "fr", None)
BAD_PAGE = CachedPage("unreadable", None, "", None, None, None, "page vide")


async def test_cache_returns_page_within_7_days_then_expires(cache: WebCache, clock: Clock) -> None:
    await cache.put_page("https://Ex.org/a#x", OK_PAGE)
    clock.advance(days=6)
    assert await cache.get_page("https://ex.org/a") == OK_PAGE
    clock.advance(days=2)
    assert await cache.get_page("https://ex.org/a") is None


async def test_unreadable_page_cached_24_hours(cache: WebCache, clock: Clock) -> None:
    await cache.put_page("https://ex.org/b", BAD_PAGE)
    clock.advance(hours=23)
    assert await cache.get_page("https://ex.org/b") == BAD_PAGE
    clock.advance(hours=2)
    assert await cache.get_page("https://ex.org/b") is None


async def test_search_results_cached_24_hours(cache: WebCache, clock: Clock) -> None:
    results = [SearchResult("Titre", "https://ex.org/", "extrait", "duckduckgo", "2026-01-01")]
    key = search_key("searxng", "RAG  cours", "fr", None, ["it", "general"])
    assert await cache.get_search(key) is None
    await cache.put_search(key, results)
    clock.advance(hours=23)
    assert await cache.get_search(key) == results
    clock.advance(hours=2)
    assert await cache.get_search(key) is None
    assert timedelta(hours=24) == SEARCH_TTL


async def test_empty_result_list_is_a_hit_not_a_miss(cache: WebCache) -> None:
    await cache.put_search("k", [])
    assert await cache.get_search("k") == []


async def test_put_replaces_an_existing_entry(cache: WebCache, db: AsyncSession) -> None:
    await cache.put_page("https://ex.org/a", BAD_PAGE)
    assert await cache.get_page("https://ex.org/a") == BAD_PAGE
    await cache.put_page("https://ex.org/a", OK_PAGE)  # même session : l'entrée chargée est relue
    assert await cache.get_page("https://ex.org/a") == OK_PAGE
    rows = (await db.execute(select(WebCacheEntry))).scalars().all()
    assert len(rows) == 1 and rows[0].status == "ok"


async def test_cache_is_per_user(
    db_session_factory: async_sessionmaker[AsyncSession], clock: Clock
) -> None:
    async with db_session_factory() as db:
        await WebCache(db, "u1", now=clock).put_page("https://ex.org/a", OK_PAGE)
        assert await WebCache(db, "u2", now=clock).get_page("https://ex.org/a") is None
        await WebCache(db, "u2", now=clock).put_page("https://ex.org/a", BAD_PAGE)
        assert await WebCache(db, "u1", now=clock).get_page("https://ex.org/a") == OK_PAGE


async def test_stored_rows_hold_hashes_not_urls_or_queries(
    cache: WebCache, db: AsyncSession
) -> None:
    await cache.put_page("https://secret.example/page?q=moi", OK_PAGE)
    await cache.put_search(search_key("brave", "ma requête privée", None, None, []), [])
    rows = (await db.execute(select(WebCacheEntry))).scalars().all()
    assert {r.kind for r in rows} == {"page", "search"}
    assert all(len(r.key_hash) == 64 and "secret" not in r.key_hash for r in rows)


async def test_malformed_payload_counts_as_a_miss(
    cache: WebCache, db: AsyncSession, clock: Clock
) -> None:
    await WebCacheRepository(db, "u1").put(
        "page", url_key("https://ex.org/old"), "ok", {"autre": 1}, clock() + timedelta(days=1)
    )
    assert await cache.get_page("https://ex.org/old") is None


def test_url_key_ignores_fragment_and_host_case() -> None:
    assert url_key("https://Ex.org/a#x") == url_key("https://ex.org/a")
    assert url_key("https://ex.org/a") != url_key("https://ex.org/b")
    with pytest.raises(AppError):
        url_key("ftp://ex.org/a")


def test_search_key_ignores_case_spaces_and_category_order() -> None:
    base = search_key("searxng", "Cours RAG", "fr", "year", ["it", "general"])
    assert base == search_key("searxng", "  cours   rag ", "fr", "year", ["general", "it"])
    assert base != search_key("brave", "cours rag", "fr", "year", ["it", "general"])
    assert base != search_key("searxng", "cours rag", "en", "year", ["it", "general"])
    assert base != search_key("searxng", "cours rag", "fr", None, ["it", "general"])
