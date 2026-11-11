"""Écriture gardée du bus (`publish_with`) : statut final et événement final dans une seule
transaction (D52 §2, D61). Jamais de statut final sans son événement, ni l'inverse."""

from contextlib import aclosing

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.bus import EventBus, Guard
from app.agents.runtime.events import SessionEvent
from app.agents.runtime.repositories import EventRepository, SessionRepository
from tests.agents.runtime.conftest import say, stored_seq, take
from tests.agents.runtime.runner_helpers import get_session

type Factory = async_sessionmaker[AsyncSession]


def _returns(value: bool) -> Guard:
    async def guard(db: AsyncSession) -> bool:
        return value

    return guard


def _complete(user_id: str, session_id: str, calls: list[bool] | None = None) -> Guard:
    """Garde du runner : `running` → `completed`, dans la transaction de l'événement."""

    async def guard(db: AsyncSession) -> bool:
        done = await SessionRepository(db, user_id).transition(
            session_id, from_={"running"}, to="completed"
        )
        if calls is not None:
            calls.append(done)
        return done

    return guard


async def _finish(
    bus: EventBus, user_id: str, session_id: str, guard: Guard
) -> SessionEvent | None:
    return await bus.publish_with(
        user_id=user_id,
        session_id=session_id,
        type="run.completed",
        payload={"summary": ""},
        guard=guard,
    )


async def test_publish_with_false_guard_writes_nothing(
    bus: EventBus, db_factory: Factory, user_id: str, session_id: str
):
    ev = await _finish(bus, user_id, session_id, _returns(False))
    assert ev is None and await stored_seq(db_factory, user_id, session_id) == 0
    assert (await say(bus, user_id, session_id, "ensuite")).seq == 1


async def test_publish_with_commits_the_guard_and_the_event_together(
    bus: EventBus, db_factory: Factory, user_id: str, session_id: str
):
    ev = await _finish(bus, user_id, session_id, _complete(user_id, session_id))
    assert ev is not None and (ev.seq, ev.type) == (1, "run.completed")
    assert (await get_session(db_factory, user_id, session_id)).status == "completed"


async def test_publish_with_rolls_back_guard_when_insert_fails(
    bus: EventBus,
    db_factory: Factory,
    user_id: str,
    session_id: str,
    monkeypatch: pytest.MonkeyPatch,
):
    """L'insertion de l'événement échoue : la garde (statut final) est annulée avec elle."""

    async def broken_add(self: EventRepository, **fields: object) -> None:
        raise RuntimeError("base indisponible")

    with monkeypatch.context() as patch:
        patch.setattr(EventRepository, "add", broken_add)
        with pytest.raises(RuntimeError):
            await _finish(bus, user_id, session_id, _complete(user_id, session_id))
    assert (await get_session(db_factory, user_id, session_id)).status == "running"
    assert await stored_seq(db_factory, user_id, session_id) == 0
    assert (await say(bus, user_id, session_id, "ensuite")).seq == 1


async def test_publish_with_reruns_the_guard_after_a_seq_conflict(
    bus: EventBus, db_factory: Factory, user_id: str, session_id: str
):
    """`seq` refusé (écrivain hors du bus) : la transaction entière est rejouée, garde comprise."""
    await say(bus, user_id, session_id, "1")
    async with db_factory() as db:
        await EventRepository(db, user_id).add(
            session_id=session_id, seq=2, type="user.message", payload={"text": "x"}
        )
        await db.commit()
    calls: list[bool] = []
    ev = await _finish(bus, user_id, session_id, _complete(user_id, session_id, calls))
    assert ev is not None and ev.seq == 3 and calls == [True, True]
    assert (await get_session(db_factory, user_id, session_id)).status == "completed"


async def test_publish_with_refused_guard_reaches_no_subscriber(
    bus: EventBus, user_id: str, session_id: str
):
    async with aclosing(bus.subscribe(user_id=user_id, session_id=session_id)) as it:
        assert await _finish(bus, user_id, session_id, _returns(False)) is None
        await say(bus, user_id, session_id, "seul")
        assert await take(it, 1) == [1]
