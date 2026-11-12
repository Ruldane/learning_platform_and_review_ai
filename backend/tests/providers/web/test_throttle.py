"""Débit par hôte du lecteur web : un départ par seconde et par hôte, 3 s pour l'API arXiv,
réservation atomique, purge des vieilles entrées, attente à chaque saut de redirection."""

import asyncio
from dataclasses import dataclass, field

import httpx
import pytest

from app.providers.web.base import UrlForbidden
from app.providers.web.throttle import DomainThrottle
from tests.providers.web.fetch_support import FakeResolver, fetcher_for, html, never, redirect


@dataclass
class FakeClock:
    """Horloge figée : `sleep` note la durée sans avancer le temps (les départs réservés
    s'empilent donc comme pour des appels simultanés)."""

    now: float = 1000.0
    sleeps: list[float] = field(default_factory=list)

    def __call__(self) -> float:
        return self.now

    async def sleep(self, delay: float) -> None:
        self.sleeps.append(delay)


@pytest.fixture
def fake_clock() -> FakeClock:
    return FakeClock()


def _throttle(clock: FakeClock, **kwargs: object) -> DomainThrottle:
    return DomainThrottle(clock=clock, sleep=clock.sleep, **kwargs)  # type: ignore[arg-type]


async def test_throttle_spaces_same_host_by_one_second(fake_clock: FakeClock) -> None:
    t = _throttle(fake_clock)
    await t.wait("ex.org")
    await t.wait("ex.org")
    assert fake_clock.sleeps == [1.0]


async def test_throttle_queues_successive_departures(fake_clock: FakeClock) -> None:
    t = _throttle(fake_clock)
    await asyncio.gather(*(t.wait("ex.org") for _ in range(3)))
    assert sorted(fake_clock.sleeps) == [1.0, 2.0]


async def test_throttle_does_not_delay_other_hosts(fake_clock: FakeClock) -> None:
    t = _throttle(fake_clock)
    for host in ("a.org", "b.org", "c.org"):
        await t.wait(host)
    assert fake_clock.sleeps == []


async def test_throttle_host_is_case_insensitive(fake_clock: FakeClock) -> None:
    t = _throttle(fake_clock)
    await t.wait("Ex.ORG")
    await t.wait("ex.org")
    assert fake_clock.sleeps == [1.0]


async def test_throttle_arxiv_override_is_three_seconds(fake_clock: FakeClock) -> None:
    t = _throttle(fake_clock)
    await t.wait("export.arxiv.org")
    await t.wait("export.arxiv.org")
    await t.wait("arxiv.org")
    await t.wait("arxiv.org")
    assert fake_clock.sleeps == [3.0, 1.0]


async def test_throttle_no_wait_once_interval_has_passed(fake_clock: FakeClock) -> None:
    t = _throttle(fake_clock)
    await t.wait("ex.org")
    fake_clock.now += 1.5
    await t.wait("ex.org")
    fake_clock.now += 0.25
    await t.wait("ex.org")
    assert fake_clock.sleeps == [0.75]


async def test_throttle_purges_entries_older_than_60_s(fake_clock: FakeClock) -> None:
    t = _throttle(fake_clock)
    await t.wait("old.org")
    fake_clock.now += 61.5
    await t.wait("new.org")
    assert t.tracked_hosts() == 1


async def test_throttle_custom_interval_and_overrides(fake_clock: FakeClock) -> None:
    t = _throttle(fake_clock, interval_s=0.5, overrides={"Slow.Example": 5.0})
    for host in ("fast.org", "fast.org", "slow.example", "slow.example"):
        await t.wait(host)
    assert fake_clock.sleeps == [0.5, 5.0]


class RecordingThrottle(DomainThrottle):
    def __init__(self) -> None:
        super().__init__()
        self.hosts: list[str] = []

    async def wait(self, host: str) -> None:
        self.hosts.append(host)


async def test_fetch_throttles_each_redirect_hop() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "a.example":
            return redirect("https://b.example/fin")
        return html()

    throttle = RecordingThrottle()
    fetcher, _ = fetcher_for(handler, throttle=throttle)
    await fetcher.fetch("https://a.example/debut")
    assert throttle.hosts == ["a.example", "b.example"]


async def test_fetch_never_throttles_a_refused_address() -> None:
    throttle = RecordingThrottle()
    resolver = FakeResolver({"interne.example": ["10.0.0.5"]})
    fetcher, _ = fetcher_for(never, resolver, throttle=throttle)
    with pytest.raises(UrlForbidden):
        await fetcher.fetch("https://interne.example/")
    assert throttle.hosts == []
