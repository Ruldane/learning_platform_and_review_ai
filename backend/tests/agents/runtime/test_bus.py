"""Bus d'événements : séquence par session, validation, rejeu fusionné au direct.

Les courses (Review Focus 2 et 4) sont provoquées de façon déterministe : publication glissée
entre l'inscription de l'abonné et la lecture en base, écrivains concurrents.
"""

import asyncio
from contextlib import aclosing

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.bus import EventBus
from app.agents.runtime.events import CostUpdatedPayload, SessionEvent
from app.agents.runtime.repositories import EventRepository
from app.core.errors import AppError
from tests.agents.runtime.conftest import say, take

type Factory = async_sessionmaker[AsyncSession]


# --- Séquence ------------------------------------------------------------------------------


async def test_publish_assigns_increasing_seq(bus: EventBus, user_id: str, session_id: str):
    a = await say(bus, user_id, session_id, "a")
    b = await say(bus, user_id, session_id, "b")
    assert (a.seq, b.seq) == (1, 2)
    assert a.type == "user.message" and a.session_id == session_id
    assert a.payload.model_dump() == {"text": "a"}


async def test_concurrent_publish_yields_unique_increasing_seq(
    bus: EventBus, user_id: str, session_id: str
):
    evs = await asyncio.gather(*[say(bus, user_id, session_id, str(i)) for i in range(50)])
    assert sorted(e.seq for e in evs) == list(range(1, 51))


async def test_graph_and_cost_writers_keep_seq_unique_and_increasing(
    bus: EventBus, user_id: str, session_id: str
):
    """Flux du graphe et callback de coût publient en même temps (Review Focus 4)."""
    cost = CostUpdatedPayload(tokens_in=1, tokens_out=1, cost_usd=0.0, cap_tokens=300_000)

    async def graph() -> list[SessionEvent]:
        return [await say(bus, user_id, session_id, str(i)) for i in range(30)]

    async def costs() -> list[SessionEvent]:
        return [
            await bus.publish(
                user_id=user_id, session_id=session_id, type="cost.updated", payload=cost
            )
            for _ in range(30)
        ]

    a, b = await asyncio.gather(graph(), costs())
    assert sorted(e.seq for e in a + b) == list(range(1, 61))
    assert [e.seq for e in a] == sorted(e.seq for e in a)
    assert [e.seq for e in b] == sorted(e.seq for e in b)


async def test_seq_continues_from_database_after_restart(
    db_factory: Factory, user_id: str, session_id: str
):
    await say(EventBus(db_factory), user_id, session_id, "avant")
    restarted = EventBus(db_factory)  # cache vide : repart de max_seq
    assert await restarted.last_seq(user_id=user_id, session_id=session_id) == 1
    assert (await say(restarted, user_id, session_id, "après")).seq == 2


async def test_unique_constraint_is_the_safety_net_for_a_foreign_writer(
    bus: EventBus, db_factory: Factory, user_id: str, session_id: str
):
    await say(bus, user_id, session_id, "1")
    async with db_factory() as db:  # écrivain hors du bus : le cache du bus devient périmé
        await EventRepository(db, user_id).add(
            session_id=session_id, seq=2, type="user.message", payload={"text": "x"}
        )
        await db.commit()
    assert (await say(bus, user_id, session_id, "3")).seq == 3


# --- Validation et isolation ---------------------------------------------------------------


async def test_publish_rejects_invalid_payload(bus: EventBus, user_id: str, session_id: str):
    with pytest.raises(ValueError):
        await bus.publish(user_id=user_id, session_id=session_id, type="cost.updated", payload={})
    assert await bus.last_seq(user_id=user_id, session_id=session_id) == 0


async def test_publish_drops_fields_outside_the_catalogue(
    bus: EventBus, db_factory: Factory, user_id: str, session_id: str
):
    """Un champ non prévu (une clé, par exemple) n'est ni persisté ni diffusé."""
    ev = await bus.publish(
        user_id=user_id,
        session_id=session_id,
        type="user.message",
        payload={"text": "a", "api_key": "sk-secret"},
    )
    assert ev.payload.model_dump() == {"text": "a"}
    async with db_factory() as db:
        rows = await EventRepository(db, user_id).list_after(session_id, 0)
    assert rows[0].payload == {"text": "a"}


async def test_publish_refuses_a_session_of_another_user(
    bus: EventBus, user_id: str, other_user_id: str, session_id: str
):
    with pytest.raises(AppError) as exc:
        await say(bus, other_user_id, session_id, "intrus")
    assert exc.value.code == "session_not_found"
    assert await bus.last_seq(user_id=user_id, session_id=session_id) == 0


async def test_subscriber_of_another_user_receives_nothing(
    bus: EventBus, user_id: str, other_user_id: str, session_id: str
):
    await say(bus, user_id, session_id, "1")
    async with aclosing(bus.subscribe(user_id=other_user_id, session_id=session_id)) as it:
        reader = asyncio.ensure_future(anext(it))
        await asyncio.sleep(0.05)
        await say(bus, user_id, session_id, "2")
        await asyncio.sleep(0.05)
        assert not reader.done()
        reader.cancel()
        with pytest.raises(asyncio.CancelledError):
            await reader


# --- Rejeu fusionné au direct (Review Focus 2) ---------------------------------------------


async def test_subscribe_merges_replay_and_live_without_gap_or_duplicate(
    bus: EventBus, user_id: str, session_id: str
):
    for text in "abc":
        await say(bus, user_id, session_id, text)
    async with aclosing(bus.subscribe(user_id=user_id, session_id=session_id, after_seq=1)) as it:
        seqs_received = await take(it, 1)
        publishers = asyncio.gather(*[say(bus, user_id, session_id, t) for t in "def"])
        seqs_received += await take(it, 4)
        await publishers
    assert seqs_received == [2, 3, 4, 5, 6]


async def test_subscribe_drops_live_duplicates_of_replayed_events(
    bus: EventBus, user_id: str, session_id: str, monkeypatch: pytest.MonkeyPatch
):
    """Course forcée : 4 est publié après l'inscription mais avant la lecture en base (il est
    à la fois relu et en file), 5 juste après la lecture (seulement en file)."""
    for text in "abc":
        await say(bus, user_id, session_id, text)
    original = bus._read_after
    calls = 0

    async def racing_read(user_id: str, session_id: str, after_seq: int) -> list[SessionEvent]:
        nonlocal calls
        calls += 1
        if calls > 1:
            return await original(user_id, session_id, after_seq)
        await say(bus, user_id, session_id, "d")
        rows = await original(user_id, session_id, after_seq)
        await say(bus, user_id, session_id, "e")
        return rows

    monkeypatch.setattr(bus, "_read_after", racing_read)
    async with aclosing(bus.subscribe(user_id=user_id, session_id=session_id, after_seq=1)) as it:
        seqs = await take(it, 4)
        await say(bus, user_id, session_id, "f")
        seqs += await take(it, 1)
    assert seqs == [2, 3, 4, 5, 6]


async def test_reconnect_with_last_seq_resumes_without_duplicates(
    bus: EventBus, user_id: str, session_id: str
):
    for text in "ab":
        await say(bus, user_id, session_id, text)
    async with aclosing(bus.subscribe(user_id=user_id, session_id=session_id)) as it:
        first = await take(it, 2)
    for text in "cd":  # publiés pendant la déconnexion
        await say(bus, user_id, session_id, text)
    async with aclosing(bus.subscribe(user_id=user_id, session_id=session_id, after_seq=2)) as it:
        second = await take(it, 2)
    assert first + second == [1, 2, 3, 4]


async def test_replay_reads_the_database_in_batches(
    db_factory: Factory, user_id: str, session_id: str
):
    bus = EventBus(db_factory, replay_batch=2)
    for i in range(5):
        await say(bus, user_id, session_id, str(i))
    async with aclosing(bus.subscribe(user_id=user_id, session_id=session_id)) as it:
        seqs = await take(it, 5)
        await say(bus, user_id, session_id, "direct")
        seqs += await take(it, 1)
    assert seqs == [1, 2, 3, 4, 5, 6]


async def test_live_gap_from_a_foreign_writer_is_filled_by_replay(
    bus: EventBus, db_factory: Factory, user_id: str, session_id: str
):
    """Un écrivain hors du bus insère 2 : le direct reçoit 3 alors que l'abonné en est à 1 ;
    il repasse par la base depuis 1 au lieu de sauter 2."""
    async with aclosing(bus.subscribe(user_id=user_id, session_id=session_id)) as it:
        reader = asyncio.ensure_future(anext(it))
        async with asyncio.timeout(5):  # inscrit : 1 arrive par le direct ou par le rejeu
            while bus.subscriber_count(user_id=user_id, session_id=session_id) == 0:
                await asyncio.sleep(0.01)
        await say(bus, user_id, session_id, "1")
        assert (await asyncio.wait_for(reader, 5)).seq == 1
        async with db_factory() as db:
            await EventRepository(db, user_id).add(
                session_id=session_id, seq=2, type="user.message", payload={"text": "étranger"}
            )
            await db.commit()
        assert (await say(bus, user_id, session_id, "3")).seq == 3
        assert await take(it, 2) == [2, 3]
        await say(bus, user_id, session_id, "4")
        assert await take(it, 1) == [4]
