"""SessionRunner : reprise, réponses en double, messages, pause, annulation, isolation."""

import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime import control
from app.agents.runtime.bus import EventBus
from app.agents.runtime.runner import SessionRunner
from app.core.errors import AppError
from tests.agents.graphs_for_tests import Probe
from tests.agents.runtime.runner_helpers import (
    final_state,
    get_session,
    types,
    wait_idle,
    wait_status,
    wait_until,
)

type Factory = async_sessionmaker[AsyncSession]


async def _asked(runner: SessionRunner, db: Factory, user_id: str) -> tuple[str, str]:
    sid = await runner.start(user_id, "ask", {})
    row = await wait_status(db, user_id, sid, "waiting_user")
    await wait_idle(runner, sid)
    assert row.pending_interrupt is not None
    return sid, row.pending_interrupt["interrupt_id"]


# --- Réponses en double ou périmées (Review Focus 5) ----------------------------------------


async def test_resume_twice_is_rejected(
    runner: SessionRunner, db_factory: Factory, user_id: str, probe: Probe
):
    sid, iid = await _asked(runner, db_factory, user_id)
    await runner.resume(user_id, sid, iid, "oui")
    with pytest.raises(AppError) as e:
        await runner.resume(user_id, sid, iid, "oui")
    assert e.value.status_code == 409
    assert e.value.message == "Cette question a déjà reçu une réponse."
    await wait_status(db_factory, user_id, sid, "completed")
    await wait_idle(runner, sid)
    assert probe.counter["after"] == 1


async def test_concurrent_double_click_resumes_the_graph_once(
    runner: SessionRunner, db_factory: Factory, user_id: str, probe: Probe
):
    sid, iid = await _asked(runner, db_factory, user_id)
    results = await asyncio.gather(
        runner.resume(user_id, sid, iid, "oui"),
        runner.resume(user_id, sid, iid, "oui"),
        return_exceptions=True,
    )
    errors = [r for r in results if isinstance(r, AppError)]
    assert results.count(None) == 1 and len(errors) == 1 and errors[0].status_code == 409
    await wait_status(db_factory, user_id, sid, "completed")
    await wait_idle(runner, sid)
    assert probe.counter["after"] == 1


async def test_stale_interrupt_id_is_rejected_and_the_question_stays(
    runner: SessionRunner, db_factory: Factory, user_id: str
):
    sid, iid = await _asked(runner, db_factory, user_id)
    with pytest.raises(AppError) as e:
        await runner.resume(user_id, sid, "perime", "oui")
    assert (e.value.code, e.value.status_code) == ("stale_interrupt", 409)
    row = await get_session(db_factory, user_id, sid)
    assert row.status == "waiting_user" and row.pending_interrupt is not None
    await runner.resume(user_id, sid, iid, "oui")
    await wait_status(db_factory, user_id, sid, "completed")


async def test_resume_of_a_running_session_is_rejected(
    runner: SessionRunner, db_factory: Factory, user_id: str, probe: Probe
):
    sid = await runner.start(user_id, "blocking", {})
    await wait_until(probe.b_started.is_set)
    with pytest.raises(AppError) as e:
        await runner.resume(user_id, sid, None, None)
    assert (e.value.code, e.value.status_code) == ("session_not_resumable", 409)


async def test_other_user_cannot_resume(
    runner: SessionRunner, db_factory: Factory, user_id: str, other_user_id: str
):
    sid, iid = await _asked(runner, db_factory, user_id)
    for action in (
        runner.resume(other_user_id, sid, iid, "x"),
        runner.pause(other_user_id, sid),
        runner.cancel(other_user_id, sid),
        runner.post_message(other_user_id, sid, "intrus"),
    ):
        with pytest.raises(AppError) as e:
            await action
        assert e.value.status_code == 404
    assert (await get_session(db_factory, user_id, sid)).status == "waiting_user"


# --- Messages de l'utilisatrice (D4) --------------------------------------------------------


async def test_post_message_is_visible_to_next_turn(
    runner: SessionRunner, db_factory: Factory, user_id: str, checkpointer: object
):
    sid, iid = await _asked(runner, db_factory, user_id)
    event = await runner.post_message(user_id, sid, "Plutôt en SQL")
    assert event.type == "user.message" and event.agent is None
    await runner.resume(user_id, sid, iid, "oui")
    await wait_status(db_factory, user_id, sid, "completed")
    await wait_idle(runner, sid)
    assert (await final_state(checkpointer, sid))["heard"] == ["Plutôt en SQL"]  # type: ignore[arg-type]


async def test_post_message_to_a_finished_session_is_rejected(
    runner: SessionRunner, db_factory: Factory, user_id: str
):
    sid = await runner.start(user_id, "two_steps", {})
    await wait_status(db_factory, user_id, sid, "completed")
    await wait_idle(runner, sid)
    with pytest.raises(AppError) as e:
        await runner.post_message(user_id, sid, "trop tard")
    assert e.value.status_code == 409


# --- Pause et annulation --------------------------------------------------------------------


async def test_pause_then_resume_with_null_interrupt(
    runner: SessionRunner, db_factory: Factory, user_id: str, probe: Probe
):
    sid = await runner.start(user_id, "blocking", {})
    await wait_until(probe.b_started.is_set)
    paused = await runner.pause(user_id, sid)
    assert paused.status == "paused" and not runner.is_active(sid)
    probe.release_b.set()
    await runner.resume(user_id, sid, None, None)
    await wait_status(db_factory, user_id, sid, "completed")
    assert probe.counter["A"] == 1  # reprise sur le dernier checkpoint : A ne rejoue pas
    assert probe.counter["B"] == 2  # B, interrompu en cours, recommence


async def test_paused_question_is_asked_again_on_resume(
    runner: SessionRunner, db_factory: Factory, user_id: str
):
    sid, iid = await _asked(runner, db_factory, user_id)
    paused = await runner.pause(user_id, sid)
    assert paused.status == "paused" and paused.pending_interrupt is None
    with pytest.raises(AppError) as e:
        await runner.resume(user_id, sid, iid, "oui")
    assert e.value.code == "stale_interrupt"
    await runner.resume(user_id, sid, None, None)
    row = await wait_status(db_factory, user_id, sid, "waiting_user")
    assert row.pending_interrupt is not None and row.pending_interrupt["interrupt_id"] == iid


async def test_cancel_marks_cancelled_and_stops_task(
    runner: SessionRunner, db_factory: Factory, user_id: str, probe: Probe
):
    sid = await runner.start(user_id, "blocking", {})
    await wait_until(probe.b_started.is_set)
    cancelled = await runner.cancel(user_id, sid)
    assert cancelled.status == "cancelled" and not runner.is_active(sid)
    probe.release_b.set()  # une tâche survivante finirait B et publierait run.completed
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(probe.b_done.wait(), 0.3)
    assert "run.completed" not in await types(db_factory, user_id, sid)
    for action in (runner.resume(user_id, sid, None, None), runner.pause(user_id, sid)):
        with pytest.raises(AppError) as e:
            await action
        assert e.value.status_code == 409


async def test_finished_session_cannot_be_paused_or_cancelled(
    runner: SessionRunner, db_factory: Factory, user_id: str
):
    sid = await runner.start(user_id, "two_steps", {})
    await wait_status(db_factory, user_id, sid, "completed")
    await wait_idle(runner, sid)
    for action in (runner.pause(user_id, sid), runner.cancel(user_id, sid)):
        with pytest.raises(AppError) as e:
            await action
        assert e.value.status_code == 409
    assert (await get_session(db_factory, user_id, sid)).status == "completed"


async def test_pause_returns_once_the_stopped_task_s_publications_are_written(
    runner: SessionRunner,
    bus: EventBus,
    user_id: str,
    probe: Probe,
    monkeypatch: pytest.MonkeyPatch,
):
    """D56 : `last_seq` de la réponse couvre tout ce que la tâche arrêtée publiait (un
    `agent.started` en vol ne doit pas arriver au front APRÈS une réponse qui l'ignore)."""
    flushed: list[bool] = []
    real_flush = bus.flush

    async def flush() -> None:
        flushed.append(runner.is_active(sid))  # la tâche est déjà arrêtée
        await real_flush()

    monkeypatch.setattr(bus, "flush", flush)
    sid = await runner.start(user_id, "blocking", {})
    await wait_until(probe.b_started.is_set)
    await runner.pause(user_id, sid)
    assert flushed == [False]


async def test_post_message_waits_for_a_control_action_in_progress(
    runner: SessionRunner, db_factory: Factory, user_id: str
):
    """M7 : un message ne se glisse pas pendant une annulation (écrit après `cancelled`)."""
    sid, _ = await _asked(runner, db_factory, user_id)
    async with runner._control(sid):  # une annulation tient le verrou de contrôle
        posting = asyncio.create_task(runner.post_message(user_id, sid, "trop tard ?"))
        await asyncio.sleep(0.05)
        assert not posting.done()
        await control.claim_cancel(db_factory, user_id, sid)
    with pytest.raises(AppError) as e:
        await posting
    assert e.value.code == "session_closed"
    assert "user.message" not in await types(db_factory, user_id, sid)
