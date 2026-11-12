from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.research import SOURCE_THRESHOLD, Source, WebQuery
from app.features.research.repository import (
    SearchUsageRepository,
    SourceRepository,
    WebCacheRepository,
    WebQueryRepository,
    month_total,
)

T0 = datetime(2026, 11, 12, tzinfo=UTC)


def _source(session_id: str | None, url_hash: str, **fields: Any) -> Source:
    values: dict[str, Any] = {"url": f"https://ex.org/{url_hash}", "status": "ok", **fields}
    return Source(session_id=session_id, url_hash=url_hash, **values)


def test_threshold_is_60() -> None:
    assert SOURCE_THRESHOLD == 60


async def test_web_cache_get_ignores_expired_and_other_users(db: AsyncSession) -> None:
    repo = WebCacheRepository(db, "u1")
    await repo.put("page", "h1", "ok", {"a": 1}, T0 + timedelta(hours=1))
    entry = await repo.get("page", "h1", T0)
    assert entry is not None and entry.payload == {"a": 1} and entry.user_id == "u1"
    assert await repo.get("page", "h1", T0 + timedelta(hours=1)) is None  # expirée à l'instant
    assert await repo.get("search", "h1", T0) is None
    assert await WebCacheRepository(db, "u2").get("page", "h1", T0) is None


async def test_web_cache_put_upserts_and_purge_is_per_user(db: AsyncSession) -> None:
    repo = WebCacheRepository(db, "u1")
    await repo.put("page", "h1", "unreadable", {"v": 1}, T0 + timedelta(hours=1))
    await repo.put("page", "h1", "ok", {"v": 2}, T0 + timedelta(days=7))
    await repo.put("page", "h2", "ok", {}, T0 + timedelta(hours=1))
    await WebCacheRepository(db, "u2").put("page", "h3", "ok", {}, T0 + timedelta(hours=1))
    entry = await repo.get("page", "h1", T0)
    assert entry is not None and (entry.status, entry.payload) == ("ok", {"v": 2})
    assert await repo.purge_expired(T0 + timedelta(days=1)) == 1  # h2 seule : h3 est à u2
    assert await repo.purge_expired(T0 + timedelta(days=1)) == 0
    assert await WebCacheRepository(db, "u2").get("page", "h3", T0) is not None


async def test_source_defaults_and_lookup_per_session_and_user(db: AsyncSession) -> None:
    repo = SourceRepository(db, "u1")
    added = await repo.add(_source("s1", "h1", user_id="intrus"))
    assert added.user_id == "u1" and added.kind == "page" and added.verdict == "pending"
    assert added.score is None and added.score_detail is None and added.summary is None
    assert (await repo.get_by_url("s1", "h1")) is added
    assert await repo.get_by_url("s2", "h1") is None
    assert await SourceRepository(db, "u2").get_by_url("s1", "h1") is None


async def test_source_unique_per_session_url(db: AsyncSession) -> None:
    repo = SourceRepository(db, "u1")
    await repo.add(_source("s1", "h1"))
    await repo.add(_source("s2", "h1"))  # une autre session peut citer la même page
    await SourceRepository(db, "u2").add(_source("s1", "h1"))
    with pytest.raises(IntegrityError):
        await repo.add(_source("s1", "h1"))


async def test_count_pages_and_list_for_session(db: AsyncSession) -> None:
    repo = SourceRepository(db, "u1")
    await repo.add(_source("s1", "h1", score=70, score_detail={"authority": 30}))
    await repo.add(_source("s1", "h2", status="unreadable"))
    await repo.add(_source("s1", "h3", kind="person"))
    await repo.add(_source("s2", "h4"))
    await SourceRepository(db, "u2").add(_source("s1", "h5"))
    assert await repo.count_pages("s1") == 2
    assert await repo.count_pages("vide") == 0
    listed = await repo.list_for_session("s1")
    assert [s.url_hash for s in listed] == ["h1", "h2", "h3"]
    assert listed[0].score_detail == {"authority": 30}


def _query(session_id: str, query_hash: str) -> WebQuery:
    return WebQuery(session_id=session_id, query_hash=query_hash, query="cours rag")


async def test_web_query_unique_per_session(db: AsyncSession) -> None:
    repo = WebQueryRepository(db, "u1")
    added = await repo.add(_query("s1", "q1"))
    assert added.user_id == "u1" and added.result_count == 0 and added.provider is None
    await repo.add(_query("s2", "q1"))
    await WebQueryRepository(db, "u2").add(_query("s1", "q1"))
    with pytest.raises(IntegrityError):
        await repo.add(_query("s1", "q1"))


async def test_web_query_get_and_count_are_scoped(db: AsyncSession) -> None:
    repo = WebQueryRepository(db, "u1")
    await repo.add(_query("s1", "q1"))
    await repo.add(_query("s1", "q2"))
    await WebQueryRepository(db, "u2").add(_query("s1", "q3"))
    assert await repo.count("s1") == 2 and await repo.count("s2") == 0
    assert await repo.get("s1", "q1") is not None
    assert await repo.get("s1", "q3") is None


async def test_increment_counts_per_provider_month_and_key(db: AsyncSession) -> None:
    repo = SearchUsageRepository(db, "u1")
    for _ in range(3):
        await repo.increment("brave", "2026-11", "fp1")
    await repo.increment("brave", "2026-12", "fp1")
    await repo.increment("brave", "2026-11", "fp2")
    assert await month_total(db, provider="brave", month="2026-11", fingerprint="fp1") == 3
    assert await month_total(db, provider="brave", month="2026-11", fingerprint="fp2") == 1
    assert await month_total(db, provider="brave", month="2026-10", fingerprint="fp1") == 0


async def test_month_total_sums_all_users_for_same_key(db: AsyncSession) -> None:
    await SearchUsageRepository(db, "u1").increment("brave", "2026-11", "fp1")
    await SearchUsageRepository(db, "u1").increment("brave", "2026-11", "fp1")
    await SearchUsageRepository(db, "u2").increment("brave", "2026-11", "fp1")
    await SearchUsageRepository(db, "u2").increment("brave", "2026-11", "autre")
    assert await month_total(db, provider="brave", month="2026-11", fingerprint="fp1") == 3
    assert await month_total(db, provider="searxng", month="2026-11", fingerprint="fp1") == 0
