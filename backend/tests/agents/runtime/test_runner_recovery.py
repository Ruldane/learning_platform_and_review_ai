"""Redémarrage du back pendant une session (Review Focus 1) : deux runners successifs sur la
même base et le même `checkpoints.db`, chacun avec son bus et son checkpointer, comme deux
processus qui se suivent."""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AsyncExitStack
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.bus import EventBus
from app.agents.runtime.checkpointer import open_checkpointer
from app.agents.runtime.repositories import SessionRepository
from app.agents.runtime.runner import SessionRunner
from app.features.settings.service import SettingsRunReader
from tests.agents.graphs_for_tests import TEST_GRAPHS, Probe
from tests.agents.runtime.runner_helpers import (
    all_events,
    fake_llm,
    get_session,
    wait_idle,
    wait_status,
    wait_until,
)

type Factory = async_sessionmaker[AsyncSession]
type MakeRunner = Callable[[], Awaitable[SessionRunner]]


@pytest.fixture
async def make_runner(
    tmp_path: Path, db_factory: Factory, probe: Probe
) -> AsyncIterator[MakeRunner]:
    async with AsyncExitStack() as stack:

        async def make() -> SessionRunner:
            checkpointer = await stack.enter_async_context(
                open_checkpointer(tmp_path / "checkpoints.db")
            )
            bus = EventBus(db_factory)
            runner = SessionRunner(
                session_factory=db_factory,
                bus=bus,
                models=fake_llm([]),
                checkpointer=checkpointer,
                prices={},
                run_settings=SettingsRunReader(db_factory),
                graphs=TEST_GRAPHS,
            )
            stack.push_async_callback(bus.aclose)
            stack.push_async_callback(runner.shutdown)
            return runner

        yield make
        probe.release_b.set()


async def test_recover_after_restart_does_not_repeat_completed_nodes(
    make_runner: MakeRunner, db_factory: Factory, user_id: str, probe: Probe
):
    r1 = await make_runner()
    sid = await r1.start(user_id, "blocking", {})
    await wait_until(lambda: probe.counter["A"] == 1 and probe.b_started.is_set())
    await r1.shutdown()  # simule l'arrêt du conteneur
    assert not r1.is_active(sid)
    assert (await get_session(db_factory, user_id, sid)).status == "running"
    r2 = await make_runner()
    probe.release_b.set()
    assert await r2.recover_on_startup() == [sid]
    await wait_status(db_factory, user_id, sid, "completed")
    await wait_idle(r2, sid)
    assert probe.counter["A"] == 1
    seqs = [e.seq for e in await all_events(db_factory, user_id, sid)]
    assert seqs == sorted(set(seqs)) and seqs[-1] == len(seqs)


async def test_waiting_session_survives_restart(
    make_runner: MakeRunner, db_factory: Factory, user_id: str, probe: Probe
):
    r1 = await make_runner()
    sid = await r1.start(user_id, "ask", {})
    await wait_status(db_factory, user_id, sid, "waiting_user")
    await wait_idle(r1, sid)
    await r1.shutdown()
    r2 = await make_runner()
    assert await r2.recover_on_startup() == []
    pending = (await get_session(db_factory, user_id, sid)).pending_interrupt
    assert pending is not None
    await r2.resume(user_id, sid, pending["interrupt_id"], "oui")
    await wait_status(db_factory, user_id, sid, "completed")
    assert probe.counter["after"] == 1


async def test_running_session_without_checkpoint_restarts_from_its_input(
    make_runner: MakeRunner, db_factory: Factory, user_id: str, probe: Probe
):
    """Arrêt avant le premier checkpoint : la reprise repart de l'entrée enregistrée."""
    async with db_factory() as db:
        row = await SessionRepository(db, user_id).add(
            graph="two_steps", status="running", input={}
        )
        await db.commit()
    runner = await make_runner()
    assert await runner.recover_on_startup() == [row.id]
    await wait_status(db_factory, user_id, row.id, "completed")
    assert (probe.counter["A"], probe.counter["B"]) == (1, 1)


async def test_shutdown_leaves_no_task_behind(
    make_runner: MakeRunner, db_factory: Factory, user_id: str, probe: Probe
):
    runner = await make_runner()
    sids = [await runner.start(user_id, "blocking", {}) for _ in range(3)]
    await wait_until(probe.b_started.is_set)
    await runner.shutdown()
    assert not any(runner.is_active(sid) for sid in sids)
    for sid in sids:
        assert (await get_session(db_factory, user_id, sid)).status == "running"
