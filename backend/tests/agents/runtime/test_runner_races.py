"""SessionRunner : courses entre actions de contrôle, et actions pendant l'arrêt du serveur.

La course est forcée de façon déterministe : la publication de `interrupt.requested` est
retenue, si bien que `resume` attend la tâche qui pose la question pendant qu'une annulation
(ou une pause) arrive.
"""

import asyncio
import gc
from typing import Any

import pytest
from langgraph.checkpoint.base import BaseCheckpointSaver
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.bus import EventBus
from app.agents.runtime.checkpointer import thread_config
from app.agents.runtime.execution import RunContext, _settle, run_session
from app.agents.runtime.repositories import SessionRepository
from app.agents.runtime.runner import SessionRunner
from app.core.errors import AppError
from app.db.models.agents import AgentSession
from app.features.settings.service import SettingsRunReader
from tests.agents.graphs_for_tests import TEST_GRAPHS, Probe
from tests.agents.runtime.runner_helpers import (
    fake_llm,
    get_session,
    types,
    wait_idle,
    wait_status,
)

type Factory = async_sessionmaker[AsyncSession]


def _hold_questions(bus: EventBus, monkeypatch: pytest.MonkeyPatch) -> asyncio.Event:
    """Retient toute publication de `interrupt.requested` jusqu'à `release.set()`."""
    release = asyncio.Event()
    original = bus.publish

    async def publish(**kwargs: Any) -> Any:
        if kwargs["type"] == "interrupt.requested":
            await release.wait()
        return await original(**kwargs)

    monkeypatch.setattr(bus, "publish", publish)
    return release


async def _resume_while_question_is_published(
    runner: SessionRunner,
    db: Factory,
    user_id: str,
    release: asyncio.Event,
    control: str,
) -> tuple[str, "asyncio.Task[None]", "asyncio.Task[AgentSession]"]:
    sid = await runner.start(user_id, "ask", {})
    row = await wait_status(db, user_id, sid, "waiting_user")  # question écrite, pas publiée
    assert row.pending_interrupt is not None
    resume = asyncio.create_task(
        runner.resume(user_id, sid, row.pending_interrupt["interrupt_id"], "oui")
    )
    await wait_status(db, user_id, sid, "running")  # réponse acceptée, resume attend la tâche
    action = getattr(runner, control)(user_id, sid)
    stop = asyncio.create_task(action)
    await asyncio.sleep(0)  # l'action est entrée et attend son tour
    release.set()
    await asyncio.wait_for(resume, 5)
    await asyncio.wait_for(stop, 5)
    await wait_idle(runner, sid)
    return sid, resume, stop


async def test_cancel_during_resume_stops_the_graph_before_any_progress(
    runner: SessionRunner,
    bus: EventBus,
    db_factory: Factory,
    user_id: str,
    probe: Probe,
    monkeypatch: pytest.MonkeyPatch,
):
    release = _hold_questions(bus, monkeypatch)
    sid, _, stop = await _resume_while_question_is_published(
        runner, db_factory, user_id, release, "cancel"
    )
    assert stop.result().status == "cancelled"
    assert (await get_session(db_factory, user_id, sid)).status == "cancelled"
    assert probe.counter["after"] == 0  # le nœud suivant n'a jamais tourné
    assert (await types(db_factory, user_id, sid))[-1] == "interrupt.requested"
    assert bus.tracked_sessions() == 0  # fermé, et pas recréé par la tâche relancée


async def test_pause_during_resume_stops_the_graph_before_any_progress(
    runner: SessionRunner,
    bus: EventBus,
    db_factory: Factory,
    user_id: str,
    probe: Probe,
    monkeypatch: pytest.MonkeyPatch,
):
    release = _hold_questions(bus, monkeypatch)
    sid, _, stop = await _resume_while_question_is_published(
        runner, db_factory, user_id, release, "pause"
    )
    assert stop.result().status == "paused"
    assert probe.counter["after"] == 0
    assert (await types(db_factory, user_id, sid))[-1] == "interrupt.requested"
    await runner.resume(user_id, sid, None, None)  # la reprise repose la question
    await wait_status(db_factory, user_id, sid, "waiting_user")


# --- Pendant l'arrêt du serveur -------------------------------------------------------------


async def test_start_during_shutdown_writes_nothing(
    runner: SessionRunner, db_factory: Factory, user_id: str
):
    await runner.shutdown()
    with pytest.raises(AppError) as e:
        await runner.start(user_id, "two_steps", {})
    assert (e.value.code, e.value.status_code) == ("server_stopping", 503)
    async with db_factory() as db:
        assert await db.scalar(select(func.count()).select_from(AgentSession)) == 0


async def test_resume_during_shutdown_keeps_the_question(
    runner: SessionRunner, db_factory: Factory, user_id: str
):
    sid = await runner.start(user_id, "ask", {})
    row = await wait_status(db_factory, user_id, sid, "waiting_user")
    await wait_idle(runner, sid)
    assert row.pending_interrupt is not None
    await runner.shutdown()
    with pytest.raises(AppError) as e:
        await runner.resume(user_id, sid, row.pending_interrupt["interrupt_id"], "oui")
    assert e.value.status_code == 503
    after = await get_session(db_factory, user_id, sid)
    assert after.status == "waiting_user" and after.pending_interrupt == row.pending_interrupt


# --- Défense en profondeur et issue non écrite ----------------------------------------------


async def test_task_started_after_a_pause_writes_nothing(
    bus: EventBus,
    db_factory: Factory,
    user_id: str,
    checkpointer: BaseCheckpointSaver[Any],
):
    """Une tâche qui démarre alors que la session n'est plus `running` s'arrête sans rien
    écrire ni publier (garde de `prepare`, en plus du verrou de contrôle)."""
    async with db_factory() as db:
        row = await SessionRepository(db, user_id).add(graph="two_steps", status="paused")
        await db.commit()
    ctx = RunContext(
        db_factory, bus, fake_llm([]), checkpointer, {}, TEST_GRAPHS, SettingsRunReader(db_factory)
    )
    await run_session(ctx, user_id, row.id, None)
    assert (await get_session(db_factory, user_id, row.id)).status == "paused"
    assert await types(db_factory, user_id, row.id) == []
    assert await checkpointer.aget_tuple(thread_config(row.id)) is None


async def test_outcome_failure_during_cancellation_is_logged_not_lost(
    caplog: pytest.LogCaptureFixture,
):
    started = asyncio.Event()

    async def failing_outcome() -> None:
        started.set()
        await asyncio.sleep(0.05)
        raise RuntimeError("base indisponible")

    task = asyncio.create_task(_settle(failing_outcome()))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    del task
    gc.collect()
    await asyncio.sleep(0)
    assert "Issue d'une session non écrite (RuntimeError)" in caplog.text
    assert "never retrieved" not in caplog.text
