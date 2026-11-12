import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import AppError
from app.features.research.repository import WebCacheRepository, WebQueryRepository
from app.features.research.service.errors import (
    BRAVE_MONTHLY_CAP,
    QUOTA_CODE,
    NoSearchProvider,
    WebQuotaReached,
)
from app.features.research.service.runtime import ResearchRuntime
from app.features.research.service.searching import SearchOutcome, search
from app.providers.search.base import SearchUnavailable
from app.providers.search.fake import FakeSearch
from tests.features.research.conftest import (
    BRAVE_KEY,
    OTHER,
    UID,
    BraveFactory,
    Clock,
    brave_total,
    hit,
    seed_brave_usage,
    set_settings,
)

Factory = async_sessionmaker[AsyncSession]


async def count_queries(factory: Factory, session_id: str, user_id: str = UID) -> int:
    async with factory() as session:
        return await WebQueryRepository(session, user_id).count(session_id)


def _urls(outcome: SearchOutcome) -> list[str]:
    return [h.result.url for h in outcome.hits]


async def test_query_is_scrubbed_before_any_provider(
    runtime: ResearchRuntime, searxng_fake: FakeSearch
) -> None:
    searxng_fake.results = {"portfolio": [hit("https://ex.org/a")]}
    out = await search(runtime, UID, None, "portfolio Jane Doé jane@x.fr")
    assert searxng_fake.calls == [("portfolio", None)]
    assert out.query == "portfolio" and out.provider == "searxng"


async def test_query_empty_after_scrub_is_refused(
    runtime: ResearchRuntime, searxng_fake: FakeSearch
) -> None:
    with pytest.raises(AppError) as error:
        await search(runtime, UID, "s1", "  Jane Doé  jane@x.fr ")
    assert (error.value.code, error.value.status_code) == ("search_query_empty", 422)
    assert "jane" not in error.value.message.lower() and searxng_fake.calls == []


async def test_falls_back_to_brave_when_searxng_fails(
    runtime_with_brave_key: ResearchRuntime,
    searxng_fake: FakeSearch,
    brave_fake: FakeSearch,
    brave_factory: BraveFactory,
    db_session_factory: Factory,
) -> None:
    searxng_fake.error = SearchUnavailable()
    brave_fake.results = {"rag": [hit("https://ex.org/rag")]}
    out = await search(runtime_with_brave_key, UID, "s1", "rag", lang="fr")
    assert out.provider == "brave" and _urls(out) == ["https://ex.org/rag"]
    assert brave_factory.keys == [BRAVE_KEY] and brave_fake.calls == [("rag", "fr")]
    assert await brave_total(db_session_factory) == 1


async def test_zero_results_fall_back_to_brave(
    runtime_with_brave_key: ResearchRuntime, searxng_fake: FakeSearch, brave_fake: FakeSearch
) -> None:
    brave_fake.results = {"rag": [hit("https://ex.org/rag")]}
    out = await search(runtime_with_brave_key, UID, None, "rag")
    assert searxng_fake.calls == [("rag", None)] and out.provider == "brave"


async def test_brave_skipped_without_key(
    runtime: ResearchRuntime, searxng_fake: FakeSearch, brave_factory: BraveFactory
) -> None:
    searxng_fake.error = SearchUnavailable()
    with pytest.raises(NoSearchProvider):
        await search(runtime, UID, "s1", "rag")
    assert brave_factory.keys == []


async def test_no_provider_left_is_readable(
    runtime: ResearchRuntime, searxng_fake: FakeSearch, db_session_factory: Factory
) -> None:
    searxng_fake.error = SearchUnavailable()
    with pytest.raises(NoSearchProvider) as error:
        await search(runtime, UID, "s1", "rag")
    assert error.value.status_code == 503 and "moteur" in error.value.message
    assert error.value.code == "search_unavailable"
    assert await count_queries(db_session_factory, "s1") == 0  # rien à rejouer


async def test_provider_order_from_settings(
    runtime_with_brave_key: ResearchRuntime,
    searxng_fake: FakeSearch,
    brave_fake: FakeSearch,
    db_session_factory: Factory,
) -> None:
    await set_settings(db_session_factory, UID, search_provider_order=["brave", "searxng"])
    searxng_fake.results = {"rag": [hit("https://ex.org/s")]}
    brave_fake.results = {"rag": [hit("https://ex.org/b")]}
    out = await search(runtime_with_brave_key, UID, None, "rag")
    assert out.provider == "brave" and searxng_fake.calls == []


async def test_excluded_domain_removed_preferred_first(
    runtime: ResearchRuntime, searxng_fake: FakeSearch
) -> None:
    searxng_fake.results = {
        "rag": [
            hit("https://www.pinterest.com/pin/1"),
            hit("https://ex.org/a"),
            hit("https://docs.python.org/3/"),
        ]
    }
    out = await search(runtime, UID, None, "rag")
    assert _urls(out) == ["https://docs.python.org/3/", "https://ex.org/a"]
    assert [h.preferred for h in out.hits] == [True, False]


async def test_query_quota_stops_at_setting(
    runtime: ResearchRuntime, searxng_fake: FakeSearch, db_session_factory: Factory
) -> None:
    await set_settings(db_session_factory, UID, search_max_queries=2)
    searxng_fake.results = {q: [hit(f"https://ex.org/{q}")] for q in ("un", "deux", "trois")}
    await search(runtime, UID, "s1", "un")
    await search(runtime, UID, "s1", "deux")
    with pytest.raises(WebQuotaReached) as error:
        await search(runtime, UID, "s1", "trois")
    assert (error.value.code, error.value.status_code) == (QUOTA_CODE, 429)
    assert error.value.message == "Plafond de 2 requêtes atteint pour cette session."
    assert len(searxng_fake.calls) == 2
    await search(runtime, UID, "s2", "trois")  # le plafond est celui d'une session


async def test_same_query_twice_in_session_counts_once(
    runtime: ResearchRuntime, searxng_fake: FakeSearch, db_session_factory: Factory
) -> None:
    searxng_fake.results = {"rag": [hit("https://ex.org/rag")]}
    a = await search(runtime, UID, "s1", "rag")
    b = await search(runtime, UID, "s1", "  RAG ")
    assert not a.replayed and b.replayed and _urls(b) == _urls(a)
    assert len(searxng_fake.calls) == 1 and await count_queries(db_session_factory, "s1") == 1


async def test_same_query_concurrently_in_session_counts_once(
    runtime: ResearchRuntime, searxng_fake: FakeSearch, db_session_factory: Factory
) -> None:
    searxng_fake.results = {"rag": [hit("https://ex.org/rag")]}
    outcomes = await asyncio.gather(*(search(runtime, UID, "s1", "rag") for _ in range(3)))
    assert sorted(o.replayed for o in outcomes) == [False, True, True]
    assert len(searxng_fake.calls) == 1 and await count_queries(db_session_factory, "s1") == 1


async def test_replay_after_cache_expiry_never_bills_brave_again(
    runtime_with_brave_key: ResearchRuntime,
    searxng_fake: FakeSearch,
    brave_fake: FakeSearch,
    clock: Clock,
    db_session_factory: Factory,
) -> None:
    searxng_fake.error = SearchUnavailable()
    brave_fake.results = {"rag": [hit("https://ex.org/rag")]}
    await search(runtime_with_brave_key, UID, "s1", "rag")
    clock.advance(hours=25)
    with pytest.raises(NoSearchProvider):
        await search(runtime_with_brave_key, UID, "s1", "rag")
    assert len(brave_fake.calls) == 1 and await brave_total(db_session_factory) == 1
    assert await count_queries(db_session_factory, "s1") == 1


async def test_brave_stops_at_900_per_month(
    runtime_with_brave_key: ResearchRuntime,
    searxng_fake: FakeSearch,
    brave_fake: FakeSearch,
    brave_factory: BraveFactory,
    clock: Clock,
    db_session_factory: Factory,
) -> None:
    await seed_brave_usage(db_session_factory, BRAVE_MONTHLY_CAP)
    searxng_fake.error = SearchUnavailable()
    brave_fake.results = {"rag": [hit("https://ex.org/rag")]}
    with pytest.raises(NoSearchProvider):
        await search(runtime_with_brave_key, UID, None, "rag")
    assert brave_factory.keys == [] and await brave_total(db_session_factory) == 900
    clock.current = clock.current.replace(month=12, day=1, hour=0)  # mois civil UTC suivant
    out = await search(runtime_with_brave_key, UID, None, "rag")
    assert out.provider == "brave" and await brave_total(db_session_factory, "2026-12") == 1


async def test_brave_cap_is_atomic_under_concurrency(
    runtime_with_brave_key: ResearchRuntime,
    searxng_fake: FakeSearch,
    brave_fake: FakeSearch,
    brave_factory: BraveFactory,
    db_session_factory: Factory,
) -> None:
    await seed_brave_usage(db_session_factory, BRAVE_MONTHLY_CAP - 1)
    searxng_fake.error = SearchUnavailable()
    brave_fake.results = {"q": [hit("https://ex.org/q")]}
    outcomes = await asyncio.gather(
        *(search(runtime_with_brave_key, UID, f"s{i}", "q") for i in range(5)),
        return_exceptions=True,
    )
    passed = [o for o in outcomes if isinstance(o, SearchOutcome)]
    assert len(passed) == 1 and passed[0].provider == "brave"
    assert all(isinstance(o, NoSearchProvider) for o in outcomes if o not in passed)
    assert await brave_total(db_session_factory) == BRAVE_MONTHLY_CAP
    assert len(brave_factory.keys) == 1


async def test_brave_cap_shared_by_users_with_same_env_key(
    runtime_with_brave_key: ResearchRuntime,
    searxng_fake: FakeSearch,
    brave_fake: FakeSearch,
    brave_factory: BraveFactory,
    db_session_factory: Factory,
) -> None:
    await seed_brave_usage(db_session_factory, BRAVE_MONTHLY_CAP - 1, user_id=UID)
    searxng_fake.error = SearchUnavailable()
    brave_fake.results = {"rag": [hit("https://ex.org/rag")]}
    await search(runtime_with_brave_key, OTHER, None, "rag")  # la 900e, comptée pour u2
    with pytest.raises(NoSearchProvider):
        await search(runtime_with_brave_key, UID, None, "autre")
    assert len(brave_factory.keys) == 1 and await brave_total(db_session_factory) == 900


async def test_search_cache_avoids_second_provider_call_within_24h(
    runtime: ResearchRuntime, searxng_fake: FakeSearch, clock: Clock
) -> None:
    searxng_fake.results = {"rag": [hit("https://ex.org/rag")]}
    first = await search(runtime, UID, None, "rag", categories=["it", "science"])
    clock.advance(hours=23)
    second = await search(runtime, UID, "s9", "Rag", categories=["science", "it"])
    assert not first.cached and second.cached and not second.replayed
    assert second.provider == "searxng" and len(searxng_fake.calls) == 1
    clock.advance(hours=2)
    assert not (await search(runtime, UID, None, "rag", categories=["it", "science"])).cached
    assert len(searxng_fake.calls) == 2


async def test_provider_failure_is_never_cached(
    runtime: ResearchRuntime, searxng_fake: FakeSearch
) -> None:
    searxng_fake.error = SearchUnavailable()
    with pytest.raises(NoSearchProvider):
        await search(runtime, UID, None, "rag")
    searxng_fake.error = None
    with pytest.raises(NoSearchProvider):  # zéro résultat : rien en cache non plus
        await search(runtime, UID, None, "rag")
    searxng_fake.results = {"rag": [hit("https://ex.org/rag")]}
    assert not (await search(runtime, UID, None, "rag")).cached
    assert len(searxng_fake.calls) == 3


async def test_expired_cache_entries_are_purged_on_write(
    runtime: ResearchRuntime, searxng_fake: FakeSearch, clock: Clock, db_session_factory: Factory
) -> None:
    searxng_fake.results = {"a": [hit("https://ex.org/a")], "b": [hit("https://ex.org/b")]}
    await search(runtime, UID, None, "a")
    clock.advance(hours=25)
    await search(runtime, UID, None, "b")  # la purge due (plus d'une heure) retire « a »
    async with db_session_factory() as session:
        rows = await WebCacheRepository(session, UID).list()
    assert len(rows) == 1
