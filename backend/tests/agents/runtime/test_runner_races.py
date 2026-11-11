"""SessionRunner : courses entre actions de contrôle, et actions pendant l'arrêt du serveur.

La course est forcée de façon déterministe : la tâche qui pose la question est retenue juste
après l'écriture de `interrupt.requested`, si bien que `resume` attend cette tâche pendant
qu'une annulation (ou une pause) arrive.
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
    """Retient la tâche qui pose une question jusqu'à `release.set()` : statut `waiting_user` et
    `interrupt.requested` sont écrits ensemble (D61), la tâche n'a pas encore fini."""
    release = asyncio.Event()
    original = bus.publish_with

    async def publish_with(**kwargs: Any) -> Any:
        event = await original(**kwargs)
        if kwargs["type"] == "interrupt.requested":
            await release.wait()
        return event

    monkeypatch.setattr(bus, "publish_with", publish_with)
    return release


async def _resume_while_question_is_published(
    runner: SessionRunner,
    db: Factory,
    user_id: str,
    release: asyncio.Event,
    control: str,
) -> tuple[str, "asyncio.Task[None]", "asyncio.Task[AgentSession]"]:
    sid = await runner.start(user_id, "ask", {})
    row = await wait_status(db, user_id, sid, "waiting_user")  # question écrite, tâche retenue
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


# --- Pause ou annulation pendant l'écriture de l'issue (D52 §2, D61) ------------------------


def _hold_outcome(
    bus: EventBus, monkeypatch: pytest.MonkeyPatch, *, inside: bool
) -> tuple[asyncio.Event, asyncio.Event]:
    """Retient l'écriture de `run.completed` jusqu'à `release.set()` : avant la garde
    (`inside=False`), ou dans la transaction, la garde passée (`inside=True` : le verrou
    d'écriture de SQLite est tenu, une transition concurrente attend le commit)."""
    held, release = asyncio.Event(), asyncio.Event()
    original = bus.publish_with

    async def publish_with(**kwargs: Any) -> Any:
        if kwargs["type"] != "run.completed":
            return await original(**kwargs)
        guard = kwargs.pop("guard")

        async def holding(db: AsyncSession) -> bool:
            done = await guard(db)
            held.set()
            await release.wait()
            return bool(done)

        if not inside:
            held.set()
            await release.wait()
        return await original(**kwargs, guard=holding if inside else guard)

    monkeypatch.setattr(bus, "publish_with", publish_with)
    return held, release


async def _control_during_outcome(
    runner: SessionRunner,
    bus: EventBus,
    db: Factory,
    user_id: str,
    monkeypatch: pytest.MonkeyPatch,
    *,
    control: str,
    inside: bool,
) -> tuple[str, bool]:
    """Lance `two_steps`, déclenche `control` pendant l'écriture de l'issue ; rend le statut
    final et la présence de `run.completed`."""
    held, release = _hold_outcome(bus, monkeypatch, inside=inside)
    sid = await runner.start(user_id, "two_steps", {})
    await asyncio.wait_for(held.wait(), 5)
    action = asyncio.create_task(getattr(runner, control)(user_id, sid))
    if inside:
        await asyncio.sleep(0.1)  # l'action attend le verrou d'écriture de SQLite
    else:
        await wait_status(db, user_id, sid, "paused" if control == "pause" else "cancelled")
    release.set()
    try:
        await asyncio.wait_for(action, 5)
    except AppError as e:  # l'issue est passée avant : la session est déjà terminée
        assert e.status_code == 409
    await wait_idle(runner, sid)
    status = (await get_session(db, user_id, sid)).status
    return status, "run.completed" in await types(db, user_id, sid)


@pytest.mark.parametrize("inside", [False, True])
async def test_pause_during_outcome_write_leaves_one_coherent_outcome(
    runner: SessionRunner,
    bus: EventBus,
    db_factory: Factory,
    user_id: str,
    monkeypatch: pytest.MonkeyPatch,
    inside: bool,
):
    outcome = await _control_during_outcome(
        runner, bus, db_factory, user_id, monkeypatch, control="pause", inside=inside
    )
    assert outcome in {("completed", True), ("paused", False)}
    assert outcome == (("completed", True) if inside else ("paused", False))


@pytest.mark.parametrize("inside", [False, True])
async def test_cancel_during_settle_never_leaves_status_without_event(
    runner: SessionRunner,
    bus: EventBus,
    db_factory: Factory,
    user_id: str,
    monkeypatch: pytest.MonkeyPatch,
    inside: bool,
):
    """Annulation pendant `_settle` : la tâche est annulée alors que l'issue s'écrit."""
    outcome = await _control_during_outcome(
        runner, bus, db_factory, user_id, monkeypatch, control="cancel", inside=inside
    )
    assert outcome in {("completed", True), ("cancelled", False)}
    assert outcome == (("completed", True) if inside else ("cancelled", False))
    assert bus.tracked_sessions() == 0  # fermé par l'issue ou par l'annulation


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
