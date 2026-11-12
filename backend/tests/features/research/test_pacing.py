"""Cadence de Brave (revue phase 3, I1) : un départ par intervalle et par clé, attente hors
verrou, budget de l'appelant respecté, créneau rendu si l'attente est annulée."""

import asyncio

import pytest

from app.features.research.service.pacing import BRAVE_INTERVAL_S, KeyPacer


class FakeTime:
    """Horloge monotone factice : `sleep` note l'attente et avance l'horloge (si `advance`)."""

    def __init__(self, *, advance: bool = True) -> None:
        self.now = 100.0
        self.advance = advance
        self.sleeps: list[float] = []

    def clock(self) -> float:
        return self.now

    async def sleep(self, delay: float) -> None:
        self.sleeps.append(delay)
        if self.advance:
            self.now += delay


def _pacer(fake: FakeTime, interval_s: float = BRAVE_INTERVAL_S) -> KeyPacer:
    return KeyPacer(interval_s, clock=fake.clock, sleep=fake.sleep)


def test_brave_interval_is_above_one_second() -> None:
    assert BRAVE_INTERVAL_S >= 1.1


async def test_same_key_waits_the_interval_other_keys_do_not() -> None:
    fake = FakeTime()
    pacer = _pacer(fake)
    assert await pacer.wait("k1", budget_s=10)
    assert await pacer.wait("k1", budget_s=10)
    assert await pacer.wait("k2", budget_s=10)
    assert fake.sleeps == [pytest.approx(BRAVE_INTERVAL_S)]


async def test_concurrent_waits_get_distinct_slots() -> None:
    fake = FakeTime(advance=False)  # trois appels au même instant
    pacer = _pacer(fake)
    await asyncio.gather(*(pacer.wait("k", budget_s=10) for _ in range(3)))
    assert sorted(fake.sleeps) == [pytest.approx(BRAVE_INTERVAL_S), pytest.approx(2.2)]


async def test_slot_beyond_budget_is_refused_without_reserving() -> None:
    fake = FakeTime()
    pacer = _pacer(fake, interval_s=5.0)
    assert await pacer.wait("k", budget_s=10)
    assert not await pacer.wait("k", budget_s=1.0)  # prochain départ dans 5 s > 1 s
    assert fake.sleeps == []
    assert await pacer.wait("k", budget_s=10)  # le refus n'a rien repoussé
    assert fake.sleeps == [pytest.approx(5.0)]


async def test_cancelled_wait_gives_its_slot_back() -> None:
    fake = FakeTime()
    gate = asyncio.Event()

    async def sleep(delay: float) -> None:
        fake.sleeps.append(delay)
        if len(fake.sleeps) == 1:
            await gate.wait()  # la première attente reste bloquée jusqu'à l'annulation

    pacer = KeyPacer(BRAVE_INTERVAL_S, clock=fake.clock, sleep=sleep)
    assert await pacer.wait("k", budget_s=10)
    task = asyncio.create_task(pacer.wait("k", budget_s=10))
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert await pacer.wait("k", budget_s=10)  # même créneau, pas un intervalle de plus
    assert fake.sleeps == [pytest.approx(BRAVE_INTERVAL_S), pytest.approx(BRAVE_INTERVAL_S)]
