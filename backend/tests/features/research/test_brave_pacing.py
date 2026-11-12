"""Brave au service de recherche (revue phase 3, I1) : cadence d'une requête par 1,1 s et par
clé, après la réservation et avant l'appel ; réservation rendue quand Brave n'a pas servi la
requête (429, clé refusée, connexion impossible, créneau hors budget)."""

import logging
import time
from collections.abc import Sequence
from dataclasses import replace

import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.features.research.service.errors import NoSearchProvider
from app.features.research.service.pacing import BRAVE_INTERVAL_S, KeyPacer
from app.features.research.service.runtime import ResearchRuntime
from app.features.research.service.searching import search
from app.providers.search.base import (
    SearchNotServed,
    SearchResult,
    SearchUnavailable,
    TimeRange,
)
from app.providers.search.fake import FakeSearch
from tests.features.research.conftest import UID, BraveFactory, brave_total, hit, set_settings
from tests.features.research.test_pacing import FakeTime

Factory = async_sessionmaker[AsyncSession]


class TimedSearch(FakeSearch):
    """Faux Brave qui note l'instant (horloge de la cadence) de chaque appel."""

    def __init__(self, fake: FakeTime) -> None:
        super().__init__("brave")
        self.fake = fake
        self.started: list[float] = []

    async def search(
        self,
        query: str,
        *,
        lang: str | None = None,
        time_range: TimeRange | None = None,
        categories: Sequence[str] = (),
    ) -> list[SearchResult]:
        self.started.append(self.fake.now)
        return await super().search(query, lang=lang, time_range=time_range, categories=categories)


@pytest.fixture
def fake_time() -> FakeTime:
    return FakeTime()


@pytest.fixture
def paced(
    runtime_with_brave_key: ResearchRuntime, searxng_fake: FakeSearch, fake_time: FakeTime
) -> ResearchRuntime:
    """SearXNG en panne (connexion refusée : échec immédiat), donc chaque requête va à Brave."""
    searxng_fake.error = SearchUnavailable()
    runtime_with_brave_key.brave_pacer = KeyPacer(
        BRAVE_INTERVAL_S, clock=fake_time.clock, sleep=fake_time.sleep
    )
    return runtime_with_brave_key


async def test_back_to_back_brave_searches_are_spaced_by_the_interval(
    paced: ResearchRuntime, fake_time: FakeTime, db_session_factory: Factory
) -> None:
    timed = TimedSearch(fake_time)
    timed.results = {"q1": [hit("https://ex.org/1")], "q2": [hit("https://ex.org/2")]}
    paced.providers = replace(paced.providers, brave=BraveFactory(timed))
    await search(paced, UID, "s1", "q1")
    await search(paced, UID, "s1", "q2")
    assert len(timed.started) == 2
    assert timed.started[1] - timed.started[0] >= BRAVE_INTERVAL_S - 1e-9  # flottants
    assert fake_time.sleeps == [pytest.approx(BRAVE_INTERVAL_S)]
    assert await brave_total(db_session_factory) == 2


async def test_real_clock_spacing_with_a_short_interval(
    runtime_with_brave_key: ResearchRuntime, searxng_fake: FakeSearch, brave_fake: FakeSearch
) -> None:
    """Même règle avec la vraie horloge (intervalle court pour le test)."""
    searxng_fake.error = SearchUnavailable()
    runtime_with_brave_key.brave_pacer = KeyPacer(0.2)
    brave_fake.results = {"q1": [hit("https://ex.org/1")], "q2": [hit("https://ex.org/2")]}
    first = time.monotonic()
    await search(runtime_with_brave_key, UID, None, "q1")
    await search(runtime_with_brave_key, UID, None, "q2")
    assert time.monotonic() - first >= 0.2 and len(brave_fake.calls) == 2


@pytest.mark.parametrize("served", [False, True])
async def test_reservation_released_only_when_brave_did_not_serve(
    served: bool, paced: ResearchRuntime, brave_fake: FakeSearch, db_session_factory: Factory
) -> None:
    """429 (ou clé refusée, connexion impossible) : Brave n'a ni servi ni facturé, la requête
    est rendue au compteur. Autre panne (5xx, délai de lecture) : elle reste comptée."""
    brave_fake.error = SearchUnavailable() if served else SearchNotServed()
    with pytest.raises(NoSearchProvider):
        await search(paced, UID, "s1", "q")
    assert len(brave_fake.calls) == 1
    assert await brave_total(db_session_factory) == (1 if served else 0)


async def test_slot_beyond_budget_skips_brave_and_releases(
    paced: ResearchRuntime, brave_fake: FakeSearch, fake_time: FakeTime, db_session_factory: Factory
) -> None:
    paced.brave_pacer = KeyPacer(30.0, clock=fake_time.clock, sleep=fake_time.sleep)
    brave_fake.results = {"q1": [hit("https://ex.org/1")]}
    await search(paced, UID, "s1", "q1")
    with pytest.raises(NoSearchProvider):
        await search(paced, UID, "s1", "q2", budget_s=5.0)  # prochain départ dans 30 s
    assert brave_fake.calls == [("q1", None)] and fake_time.sleeps == []
    assert await brave_total(db_session_factory) == 1  # la seconde réservation est rendue


async def test_release_db_error_still_falls_back_to_next_provider(
    runtime_with_brave_key: ResearchRuntime,
    searxng_fake: FakeSearch,
    brave_fake: FakeSearch,
    db_session_factory: Factory,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Base occupée pendant le rendu d'une réservation Brave (D82) : l'erreur est avalée et
    journalisée par son type, la chaîne passe au fournisseur suivant au lieu d'échouer."""

    async def busy(*args: object, **kwargs: object) -> bool:
        raise OperationalError("UPDATE search_usage", {}, Exception("database is locked"))

    monkeypatch.setattr("app.features.research.service.chain.release_brave", busy)
    await set_settings(db_session_factory, UID, search_provider_order=["brave", "searxng"])
    brave_fake.error = SearchNotServed()
    searxng_fake.results = {"zxq secrete": [hit("https://ex.org/s")]}
    with caplog.at_level(logging.WARNING):
        out = await search(runtime_with_brave_key, UID, "s1", "zxq secrete")
    assert out.provider == "searxng" and len(brave_fake.calls) == 1
    assert "OperationalError" in caplog.text and "zxq" not in caplog.text
    assert "database is locked" not in caplog.text
