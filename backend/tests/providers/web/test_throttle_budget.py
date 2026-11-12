"""Débit sous charge (revue 3.4, I1) : un créneau hors budget n'est jamais réservé, un appel
annulé rend son créneau, une rafale ne bloque pas durablement un hôte."""

import asyncio
import time
from dataclasses import dataclass, field

import pytest

from app.providers.web.base import TIMEOUT_MESSAGE, UrlUnreadable
from app.providers.web.throttle import DomainThrottle
from tests.providers.web.fetch_support import fetcher_for, html


@dataclass
class BlockingClock:
    """Horloge réglable ; `sleep` note la durée puis bloque jusqu'à l'annulation."""

    now: float = 1000.0
    sleeps: list[float] = field(default_factory=list)

    def __call__(self) -> float:
        return self.now

    async def sleep(self, delay: float) -> None:
        self.sleeps.append(delay)
        await asyncio.Event().wait()


@dataclass
class InstantClock:
    now: float = 1000.0
    sleeps: list[float] = field(default_factory=list)

    def __call__(self) -> float:
        return self.now

    async def sleep(self, delay: float) -> None:
        self.sleeps.append(delay)


async def _cancelled(task: asyncio.Task[None]) -> None:
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


async def test_cancelled_wait_gives_its_slot_back() -> None:
    clock = BlockingClock()
    t = DomainThrottle(clock=clock, sleep=clock.sleep)
    await t.wait("ex.org")
    await _cancelled(asyncio.create_task(t.wait("ex.org")))
    instant = InstantClock()
    t._sleep = instant.sleep
    await t.wait("ex.org")
    assert clock.sleeps == [1.0] and instant.sleeps == [1.0]  # pas 2.0 : créneau rendu


async def test_cancelled_wait_restores_the_previous_departure() -> None:
    clock = BlockingClock()
    t = DomainThrottle(clock=clock, sleep=clock.sleep)
    await t.wait("ex.org")
    clock.now += 0.5
    await _cancelled(asyncio.create_task(t.wait("ex.org")))
    instant = InstantClock(now=clock.now)
    t._clock, t._sleep = instant, instant.sleep
    await t.wait("ex.org")
    assert clock.sleeps == [0.5] and instant.sleeps == [0.5]


async def test_cancelled_wait_in_the_middle_never_delays_later_ones() -> None:
    clock = BlockingClock()
    t = DomainThrottle(clock=clock, sleep=clock.sleep)
    await t.wait("ex.org")
    middle = asyncio.create_task(t.wait("ex.org"))
    last = asyncio.create_task(t.wait("ex.org"))
    await _cancelled(middle)
    await _cancelled(last)
    instant = InstantClock()
    t._sleep = instant.sleep
    await t.wait("ex.org")
    # Le créneau du milieu reste un trou ; le dernier est rendu : le suivant prend 2 s, pas 3.
    assert clock.sleeps == [1.0, 2.0] and instant.sleeps == [2.0]


async def test_wait_beyond_budget_fails_fast_without_reserving() -> None:
    clock = InstantClock()
    t = DomainThrottle(clock=clock, sleep=clock.sleep)
    await t.wait("export.arxiv.org", budget_s=10.0)
    with pytest.raises(UrlUnreadable) as caught:
        await t.wait("export.arxiv.org", budget_s=2.0)
    assert caught.value.message == TIMEOUT_MESSAGE and clock.sleeps == []
    await t.wait("export.arxiv.org", budget_s=3.0)
    assert clock.sleeps == [3.0]


async def test_arxiv_burst_beyond_budget_does_not_push_back_later_calls() -> None:
    clock = InstantClock()
    t = DomainThrottle(clock=clock, sleep=clock.sleep)
    outcomes = await asyncio.gather(
        *(t.wait("export.arxiv.org", budget_s=10.0) for _ in range(8)), return_exceptions=True
    )
    failed = [o for o in outcomes if isinstance(o, UrlUnreadable)]
    assert len(failed) == 4 and all(f.message == TIMEOUT_MESSAGE for f in failed)
    assert sorted(clock.sleeps) == [3.0, 6.0, 9.0]
    clock.now += 3.0  # une nouvelle lecture 3 s plus tard prend le créneau de 12 s
    await t.wait("export.arxiv.org", budget_s=10.0)
    assert clock.sleeps[-1] == 9.0 and t.tracked_hosts() == 1


async def test_burst_over_many_hosts_keeps_memory_bounded() -> None:
    clock = InstantClock()
    t = DomainThrottle(clock=clock, sleep=clock.sleep)
    for minute in range(5):
        for i in range(100):
            await t.wait(f"h{minute}-{i}.example", budget_s=1.0)
        clock.now += 61.0
    await t.wait("dernier.example")
    assert t.tracked_hosts() == 1


async def test_fetch_beyond_budget_fails_fast_without_request() -> None:
    sent: list[object] = []

    def handler(request: object) -> object:
        sent.append(request)
        return html()

    throttle = DomainThrottle(interval_s=100.0)
    fetcher, _ = fetcher_for(handler, throttle=throttle)  # type: ignore[arg-type]
    await fetcher.fetch("https://ex.org/a")
    started = time.monotonic()
    with pytest.raises(UrlUnreadable) as caught:
        await fetcher.fetch("https://ex.org/b")
    assert caught.value.message == TIMEOUT_MESSAGE and caught.value.__cause__ is None
    assert time.monotonic() - started < 1.0 and len(sent) == 1
