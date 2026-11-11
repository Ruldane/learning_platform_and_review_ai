import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.repositories import (
    EventRepository,
    LlmCallRepository,
    SessionRepository,
    list_sessions_to_recover,
)

type Factory = async_sessionmaker[AsyncSession]


async def _new_session(db: AsyncSession, user_id: str, status: str = "running") -> str:
    row = await SessionRepository(db, user_id).add(graph="demo_debate", status=status, input={})
    return row.id


async def _add_events(db: AsyncSession, user_id: str, session_id: str, count: int) -> None:
    repo = EventRepository(db, user_id)
    for seq in range(1, count + 1):
        await repo.add(session_id=session_id, seq=seq, type="agent.token", payload={"n": seq})


async def test_list_after_returns_ordered_events_after_seq(db_factory: Factory, user_id: str):
    async with db_factory() as db:
        session_id = await _new_session(db, user_id)
        repo = EventRepository(db, user_id)
        for seq in (3, 1, 2):  # insérés dans le désordre : le tri est celui de la requête
            await repo.add(session_id=session_id, seq=seq, type="agent.token", payload={})
        rows = await repo.list_after(session_id, after_seq=1)
    assert [r.seq for r in rows] == [2, 3]


async def test_max_seq_is_zero_when_empty(db_factory: Factory, user_id: str):
    async with db_factory() as db:
        session_id = await _new_session(db, user_id)
        assert await EventRepository(db, user_id).max_seq(session_id) == 0
        await _add_events(db, user_id, session_id, 3)
        assert await EventRepository(db, user_id).max_seq(session_id) == 3


async def test_duplicate_seq_is_rejected(db_factory: Factory, user_id: str):
    async with db_factory() as db:
        session_id = await _new_session(db, user_id)
        repo = EventRepository(db, user_id)
        await repo.add(session_id=session_id, seq=1, type="agent.token", payload={})
        with pytest.raises(IntegrityError):
            await repo.add(session_id=session_id, seq=1, type="agent.token", payload={})


async def test_event_repository_isolates_users(
    db_factory: Factory, user_id: str, other_user_id: str
):
    async with db_factory() as db:
        session_id = await _new_session(db, user_id)
        await _add_events(db, user_id, session_id, 2)
        other = EventRepository(db, other_user_id)
        assert await other.list_after(session_id, 0) == []
        assert await other.max_seq(session_id) == 0
        assert len(await EventRepository(db, user_id).list_after(session_id, 0)) == 2


async def test_deleting_a_session_cascades_to_its_events(db_factory: Factory, user_id: str):
    async with db_factory() as db:
        session_id = await _new_session(db, user_id)
        await _add_events(db, user_id, session_id, 2)
        assert await SessionRepository(db, user_id).delete(session_id)
        assert await EventRepository(db, user_id).list_after(session_id, 0) == []


async def test_session_defaults(db_factory: Factory, user_id: str):
    async with db_factory() as db:
        row = await SessionRepository(db, user_id).add(graph="g", status="running", input={"a": 1})
    assert (row.tokens_in, row.tokens_out, row.cost_usd) == (0, 0, 0.0)
    assert row.pending_interrupt is None and row.error is None
    assert row.subject_type is None and row.subject_id is None


async def test_llm_call_repository_stores_a_call(db_factory: Factory, user_id: str):
    async with db_factory() as db:
        call = await LlmCallRepository(db, user_id).add(
            provider="anthropic",
            model="m",
            tokens_in=10,
            tokens_out=5,
            latency_ms=120,
            cost_usd=0.001,
        )
    assert call.session_id is None and call.graph is None and call.agent is None


async def test_list_sessions_to_recover_only_running(
    db_factory: Factory, user_id: str, other_user_id: str
):
    async with db_factory() as db:
        s1 = await _new_session(db, user_id, "running")
        s2 = await _new_session(db, other_user_id, "running")
        await _new_session(db, user_id, "waiting_user")
        await _new_session(db, other_user_id, "completed")
        assert sorted(await list_sessions_to_recover(db)) == sorted(
            [(user_id, s1), (other_user_id, s2)]
        )
