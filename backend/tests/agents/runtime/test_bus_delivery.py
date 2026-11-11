"""Bus d'événements : abonnés lents ou partis, fin de session, annulation, verrou SQLite."""

import asyncio
from contextlib import aclosing

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.bus import EventBus
from app.agents.runtime.repositories import EventRepository, SessionRepository
from app.db.models.agents import AgentSession
from tests.agents.runtime.conftest import TIMEOUT, say, stored_seq, take

type Factory = async_sessionmaker[AsyncSession]


async def _registered(bus: EventBus, user_id: str, session_id: str, count: int = 1) -> None:
    """Attend que `count` abonnés soient inscrits (l'inscription a lieu au premier `anext`)."""
    async with asyncio.timeout(TIMEOUT):
        while bus.subscriber_count(user_id=user_id, session_id=session_id) < count:
            await asyncio.sleep(0.01)


# --- Abonnés lents (file bornée) -----------------------------------------------------------


async def test_slow_subscriber_does_not_block_publishers_and_catches_up_by_replay(
    db_factory: Factory, user_id: str, session_id: str
):
    bus = EventBus(db_factory, queue_size=3)
    async with aclosing(bus.subscribe(user_id=user_id, session_id=session_id)) as it:
        first = asyncio.ensure_future(anext(it))
        await _registered(bus, user_id, session_id)
        async with asyncio.timeout(TIMEOUT):  # l'abonné ne lit rien : publish ne bloque pas
            for i in range(20):
                await say(bus, user_id, session_id, str(i))
        seqs = [(await first).seq] + await take(it, 19)
        await say(bus, user_id, session_id, "direct")
        seqs += await take(it, 1)
    assert seqs == list(range(1, 22))


async def test_overflowed_subscriber_keeps_a_bounded_queue(
    db_factory: Factory, user_id: str, session_id: str
):
    bus = EventBus(db_factory, queue_size=3)
    async with aclosing(bus.subscribe(user_id=user_id, session_id=session_id)) as it:
        reader = asyncio.ensure_future(anext(it))
        await _registered(bus, user_id, session_id)
        await say(bus, user_id, session_id, "0")
        assert (await reader).seq == 1
        for i in range(50):
            await say(bus, user_id, session_id, str(i))
        assert bus.queued(user_id=user_id, session_id=session_id) <= 3
        assert await take(it, 50) == list(range(2, 52))


# --- Désinscription et nettoyage -----------------------------------------------------------


async def test_closing_the_iterator_unregisters_the_subscriber(
    bus: EventBus, user_id: str, session_id: str
):
    await say(bus, user_id, session_id, "a")
    async with aclosing(bus.subscribe(user_id=user_id, session_id=session_id)) as it:
        await take(it, 1)
        assert bus.subscriber_count(user_id=user_id, session_id=session_id) == 1
    assert bus.subscriber_count(user_id=user_id, session_id=session_id) == 0


async def test_cancelled_consumer_unregisters_the_subscriber(
    bus: EventBus, user_id: str, session_id: str
):
    async def consume() -> None:
        async for _ in bus.subscribe(user_id=user_id, session_id=session_id):
            pass

    task = asyncio.create_task(consume())
    await _registered(bus, user_id, session_id)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert bus.subscriber_count(user_id=user_id, session_id=session_id) == 0


async def test_close_ends_subscribers_after_pending_events_and_frees_state(
    bus: EventBus, user_id: str, session_id: str
):
    async def consume() -> list[int]:
        return [e.seq async for e in bus.subscribe(user_id=user_id, session_id=session_id)]

    task = asyncio.create_task(consume())
    await _registered(bus, user_id, session_id)
    for text in "ab":
        await say(bus, user_id, session_id, text)
    await bus.close(user_id=user_id, session_id=session_id)
    assert await asyncio.wait_for(task, TIMEOUT) == [1, 2]
    assert bus.tracked_sessions() == 0


async def test_close_still_delivers_events_dropped_by_an_overflow(
    db_factory: Factory, user_id: str, session_id: str
):
    bus = EventBus(db_factory, queue_size=2)

    async def consume() -> list[int]:
        return [e.seq async for e in bus.subscribe(user_id=user_id, session_id=session_id)]

    task = asyncio.create_task(consume())
    await _registered(bus, user_id, session_id)
    for i in range(6):
        await say(bus, user_id, session_id, str(i))
    await bus.close(user_id=user_id, session_id=session_id)
    assert await asyncio.wait_for(task, TIMEOUT) == [1, 2, 3, 4, 5, 6]


async def test_publish_after_close_starts_again_from_the_database(
    bus: EventBus, user_id: str, session_id: str
):
    await say(bus, user_id, session_id, "a")
    await bus.close(user_id=user_id, session_id=session_id)
    assert (await say(bus, user_id, session_id, "b")).seq == 2


async def test_subscriber_state_is_freed_for_a_session_never_published(
    bus: EventBus, other_user_id: str, session_id: str
):
    async with aclosing(bus.subscribe(user_id=other_user_id, session_id=session_id)) as it:
        reader = asyncio.ensure_future(anext(it))
        await _registered(bus, other_user_id, session_id)
        reader.cancel()
        with pytest.raises(asyncio.CancelledError):
            await reader
    assert bus.tracked_sessions() == 0


# --- Annulation et verrou SQLite -----------------------------------------------------------


async def test_cancelled_publisher_still_delivers_a_committed_event(
    bus: EventBus, db_factory: Factory, user_id: str, session_id: str
):
    """Le runner peut être annulé en pleine publication : un événement écrit est diffusé."""
    async with aclosing(bus.subscribe(user_id=user_id, session_id=session_id)) as it:
        reader = asyncio.ensure_future(anext(it))
        await _registered(bus, user_id, session_id)
        publisher = asyncio.create_task(say(bus, user_id, session_id, "a"))
        await asyncio.sleep(0)  # publish est entré dans l'écriture protégée
        publisher.cancel()
        with pytest.raises(asyncio.CancelledError):
            await publisher
        assert (await asyncio.wait_for(reader, TIMEOUT)).seq == 1
    assert await stored_seq(db_factory, user_id, session_id) == 1
    assert (await say(bus, user_id, session_id, "b")).seq == 2


async def test_flush_waits_for_publications_whose_caller_was_cancelled(
    bus: EventBus, db_factory: Factory, user_id: str, session_id: str
):
    """Pause : la tâche arrêtée a pu laisser une publication en vol ; `flush` l'attend, la
    réponse REST lue ensuite la compte dans `last_seq` (D56)."""
    publisher = asyncio.create_task(say(bus, user_id, session_id, "a"))
    await asyncio.sleep(0)  # publish est entré dans l'écriture protégée
    publisher.cancel()
    with pytest.raises(asyncio.CancelledError):
        await publisher
    await bus.flush()
    assert await stored_seq(db_factory, user_id, session_id) == 1
    await bus.flush()  # rien en vol : rend la main aussitôt


async def test_flush_waits_only_for_given_session(
    bus: EventBus, db_factory: Factory, user_id: str, session_id: str
):
    """N5 : la pause d'une session n'attend pas les publications des autres sessions."""
    async with db_factory() as db:
        other = await SessionRepository(db, user_id).add(graph="demo", status="running")
        await db.commit()
    held = bus._state((user_id, other.id))
    await held.lock.acquire()  # la publication de l'autre session reste bloquée
    try:
        blocked = asyncio.create_task(say(bus, user_id, other.id, "bloquée"))
        mine = asyncio.create_task(say(bus, user_id, session_id, "a"))
        await asyncio.sleep(0)  # les deux publications sont en vol
        await asyncio.wait_for(bus.flush(user_id=user_id, session_id=session_id), timeout=1)
        assert mine.done() and await stored_seq(db_factory, user_id, session_id) == 1
        flushing_other = asyncio.create_task(bus.flush(user_id=user_id, session_id=other.id))
        await asyncio.sleep(0.05)
        assert not flushing_other.done() and not blocked.done()
    finally:
        held.lock.release()
    await asyncio.wait_for(flushing_other, TIMEOUT)
    assert blocked.done() and await stored_seq(db_factory, user_id, other.id) == 1


async def test_flush_takes_a_whole_session_key(bus: EventBus, user_id: str):
    with pytest.raises(ValueError):
        await bus.flush(user_id=user_id)


async def test_publish_waits_for_a_concurrent_sqlite_writer(
    bus: EventBus, db_factory: Factory, user_id: str, session_id: str
):
    """Une autre connexion tient le verrou d'écriture : publish attend (busy timeout)."""
    await say(bus, user_id, session_id, "a")  # cache rempli : publish ne fait plus qu'écrire
    async with db_factory() as db:
        await db.execute(update(AgentSession).values(status="paused"))  # verrou d'écriture
        task = asyncio.create_task(say(bus, user_id, session_id, "b"))
        await asyncio.sleep(0.3)
        assert not task.done()
        await db.commit()
    assert (await asyncio.wait_for(task, TIMEOUT)).seq == 2


async def test_aclose_waits_for_publishes_whose_caller_was_cancelled(
    bus: EventBus,
    db_factory: Factory,
    user_id: str,
    session_id: str,
    monkeypatch: pytest.MonkeyPatch,
):
    """Arrêt du serveur : `aclose` attend les écritures protégées encore en vol (sinon le
    moteur serait fermé sous leurs pieds)."""
    entered, release = asyncio.Event(), asyncio.Event()
    original = bus._writer.insert

    async def slow_insert(*args: object, **kwargs: object) -> object:
        entered.set()
        await release.wait()
        return await original(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(bus._writer, "insert", slow_insert)
    publisher = asyncio.create_task(say(bus, user_id, session_id, "a"))
    await asyncio.wait_for(entered.wait(), TIMEOUT)
    publisher.cancel()
    with pytest.raises(asyncio.CancelledError):
        await publisher
    closing = asyncio.create_task(bus.aclose())
    await asyncio.sleep(0.05)
    assert not closing.done()
    release.set()
    await asyncio.wait_for(closing, TIMEOUT)
    async with db_factory() as db:
        assert await EventRepository(db, user_id).max_seq(session_id) == 1


async def test_aclose_without_publication_returns_at_once(bus: EventBus):
    await asyncio.wait_for(bus.aclose(), TIMEOUT)
