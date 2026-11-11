"""SessionRunner : lancement, flux traduit en événements, interruptions, échecs lisibles."""

import logging
import time
from collections.abc import Callable

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.bus import EventBus
from app.agents.runtime.deps import ChatModelSource
from app.agents.runtime.runner import SessionRunner
from app.core.errors import AppError
from app.db.models.agents import LlmCall
from tests.agents.graphs_for_tests import SECRET
from tests.agents.runtime.runner_helpers import (
    all_events,
    fake_llm,
    get_session,
    types,
    wait_idle,
    wait_status,
)

type Factory = async_sessionmaker[AsyncSession]
type MakeRunner = Callable[[ChatModelSource], SessionRunner]


async def test_start_returns_quickly_and_completes(
    runner: SessionRunner, db_factory: Factory, user_id: str
):
    t0 = time.perf_counter()
    sid = await runner.start(user_id, "two_steps", {})
    assert time.perf_counter() - t0 < 2
    await wait_status(db_factory, user_id, sid, "completed")
    await wait_idle(runner, sid)
    events = await all_events(db_factory, user_id, sid)
    assert events[-1].type == "run.completed"
    assert events[-1].payload.model_dump() == {"summary": "Deux étapes faites."}


async def test_start_stores_the_session_row(
    runner: SessionRunner, db_factory: Factory, user_id: str
):
    sid = await runner.start(
        user_id, "with_topic", {"topic": "SQL"}, subject_type="skill", subject_id="s1"
    )
    row = await get_session(db_factory, user_id, sid)
    assert (row.graph, row.input, row.subject_type, row.subject_id) == (
        "with_topic",
        {"topic": "SQL"},
        "skill",
        "s1",
    )
    await wait_idle(runner, sid)


async def test_start_rejects_an_invalid_input(runner: SessionRunner, user_id: str):
    with pytest.raises(AppError) as exc:
        await runner.start(user_id, "with_topic", {"topic": 3, "secret": "x"})
    assert (exc.value.code, exc.value.status_code) == ("invalid_input", 422)
    assert "x" not in str(exc.value.details)


async def test_start_rejects_an_unknown_graph(runner: SessionRunner, user_id: str):
    with pytest.raises(AppError) as exc:
        await runner.start(user_id, "inconnu", {})
    assert (exc.value.code, exc.value.status_code) == ("unknown_graph", 404)


async def test_llm_call_streams_events_and_records_its_cost(
    runner: SessionRunner, db_factory: Factory, user_id: str
):
    sid = await runner.start(user_id, "with_topic", {"topic": "SQL"})
    await wait_status(db_factory, user_id, sid, "completed")
    await wait_idle(runner, sid)
    events = await all_events(db_factory, user_id, sid)
    kinds = [e.type for e in events]
    assert kinds[0] == "agent.started" and kinds[-1] == "run.completed"
    tokens = [e for e in events if e.type == "agent.token"]
    assert "".join(e.payload.text for e in tokens) == "Bonjour à toi"  # type: ignore[union-attr]
    assert {e.agent for e in tokens} == {"demo"}
    assert "agent.message" in kinds and "cost.updated" in kinds
    assert [e.seq for e in events] == list(range(1, len(events) + 1))
    async with db_factory() as db:
        calls = (await db.execute(select(LlmCall))).scalars().all()
    assert [(c.session_id, c.graph, c.agent, c.model) for c in calls] == [
        (sid, "with_topic", "demo", "modele-test")
    ]
    row = await get_session(db_factory, user_id, sid)
    assert row.tokens_out == 3 and row.cost_usd > 0


async def test_structured_output_is_not_streamed_as_tokens(
    make_runner: MakeRunner, db_factory: Factory, user_id: str
):
    """Le JSON brut d'une sortie structurée n'est pas un texte pour l'utilisatrice (D44)."""
    runner = make_runner(fake_llm(['{"ok": true}']))
    sid = await runner.start(user_id, "structured", {})
    await wait_status(db_factory, user_id, sid, "completed")
    await wait_idle(runner, sid)
    kinds = await types(db_factory, user_id, sid)
    assert "agent.token" not in kinds and "cost.updated" in kinds


async def test_interrupt_sets_waiting_user_and_resume_completes(
    runner: SessionRunner, db_factory: Factory, user_id: str
):
    sid = await runner.start(user_id, "ask", {})
    row = await wait_status(db_factory, user_id, sid, "waiting_user")
    pending = row.pending_interrupt
    assert pending is not None and pending["question"] == "On continue ?"
    await wait_idle(runner, sid)
    asked = (await all_events(db_factory, user_id, sid))[-1]
    assert asked.type == "interrupt.requested"
    assert asked.payload.model_dump() == pending
    await runner.resume(user_id, sid, pending["interrupt_id"], "oui")
    assert (await get_session(db_factory, user_id, sid)).pending_interrupt is None
    await wait_status(db_factory, user_id, sid, "completed")
    await wait_idle(runner, sid)
    last = (await all_events(db_factory, user_id, sid))[-1]
    assert last.payload.model_dump() == {"summary": "Réponse : oui"}


async def test_waiting_and_paused_sessions_keep_their_bus_open(
    runner: SessionRunner, bus: EventBus, db_factory: Factory, user_id: str
):
    sid = await runner.start(user_id, "ask", {})
    await wait_status(db_factory, user_id, sid, "waiting_user")
    await wait_idle(runner, sid)
    assert bus.tracked_sessions() == 1  # pas de close sur waiting_user
    await runner.pause(user_id, sid)
    assert bus.tracked_sessions() == 1  # ni sur paused
    await runner.cancel(user_id, sid)
    assert bus.tracked_sessions() == 0


async def test_completed_session_closes_its_bus(
    runner: SessionRunner, bus: EventBus, db_factory: Factory, user_id: str
):
    sid = await runner.start(user_id, "two_steps", {})
    await wait_status(db_factory, user_id, sid, "completed")
    await wait_idle(runner, sid)
    assert bus.tracked_sessions() == 0


async def test_parallel_questions_are_asked_one_at_a_time(
    runner: SessionRunner, db_factory: Factory, user_id: str
):
    sid = await runner.start(user_id, "two_questions", {})
    asked: list[str] = []
    for answer in ("x", "y"):
        row = await wait_status(db_factory, user_id, sid, "waiting_user")
        await wait_idle(runner, sid)
        assert row.pending_interrupt is not None
        asked.append(row.pending_interrupt["question"])
        await runner.resume(user_id, sid, row.pending_interrupt["interrupt_id"], answer)
    await wait_status(db_factory, user_id, sid, "completed")
    assert sorted(asked) == ["qa", "qb"]
    published = [t for t in await types(db_factory, user_id, sid) if t == "interrupt.requested"]
    assert len(published) == 2


# --- Échecs lisibles (Review Focus 3) -------------------------------------------------------


async def test_missing_key_fails_session_readably(
    make_runner: MakeRunner, db_factory: Factory, user_id: str
):
    runner = make_runner(fake_llm(["jamais"], key=None))
    sid = await runner.start(user_id, "one_llm_call", {})
    row = await wait_status(db_factory, user_id, sid, "failed")
    await wait_idle(runner, sid)
    ev = (await all_events(db_factory, user_id, sid))[-1]
    assert ev.type == "run.failed" and ev.payload.code == "llm_key_missing"  # type: ignore[union-attr]
    assert "Aucune clé" in ev.payload.message  # type: ignore[union-attr]
    assert row.error == ev.payload.model_dump()
    assert not runner.is_active(sid)


async def test_unexpected_error_fails_with_a_generic_french_message(
    runner: SessionRunner,
    db_factory: Factory,
    user_id: str,
    caplog: pytest.LogCaptureFixture,
):
    caplog.set_level(logging.INFO)
    sid = await runner.start(user_id, "crash", {})
    await wait_status(db_factory, user_id, sid, "failed")
    await wait_idle(runner, sid)
    ev = (await all_events(db_factory, user_id, sid))[-1]
    assert ev.payload.model_dump() == {
        "code": "internal_error",
        "message": "Une erreur inattendue a interrompu la session.",
    }
    assert sid in caplog.text and SECRET not in caplog.text


async def test_token_cap_fails_the_session_before_the_call(
    runner: SessionRunner, db_factory: Factory, user_id: str
):
    sid = await runner.start(user_id, "spend_then_llm", {})
    await wait_status(db_factory, user_id, sid, "failed")
    await wait_idle(runner, sid)
    ev = (await all_events(db_factory, user_id, sid))[-1]
    assert ev.type == "run.failed" and ev.payload.code == "token_cap_reached"  # type: ignore[union-attr]
    async with db_factory() as db:
        assert (await db.execute(select(LlmCall))).first() is None
