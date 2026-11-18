import asyncio

from app.agents.runtime.playback import claim_step
from app.agents.runtime.runner import SessionRunner
from app.core.errors import AppError
from app.core.played import PLAY_CONTEXT, PlayContext
from tests.agents.graphs_for_tests import Probe
from tests.agents.runtime.runner_helpers import Factory, fake_llm, get_session, wait_idle
from tests.agents.runtime.test_runner_chain import MakeRunner, _calls


async def start(runner: SessionRunner, user_id: str, graph: str) -> str:
    flag = PLAY_CONTEXT.set(PlayContext(user_id, "claude-code"))
    try:
        return await runner.start(user_id, graph, {})
    finally:
        PLAY_CONTEXT.reset(flag)


async def step(runner: SessionRunner, db: Factory, user_id: str, sid: str) -> str:
    await wait_idle(runner, sid)
    row = await get_session(db, user_id, sid)
    assert row.status == "waiting_user" and row.pending_interrupt, row.error
    assert row.played_by == "claude-code"
    return str(row.pending_interrupt["brief"]["step_id"])


async def test_reserved_answer_survives_restart_then_child_uses_same_client(
    make_runner: MakeRunner, db_factory: Factory, user_id: str, probe: Probe
) -> None:
    runner = make_runner(fake_llm([], key=None))
    parent = await start(runner, user_id, "chain")
    first = await step(runner, db_factory, user_id, parent)
    row = await get_session(db_factory, user_id, parent)
    await claim_step(db_factory, row, first, "Réponse de la première agent.")
    await runner.shutdown()

    recovered = make_runner(fake_llm([], key=None))
    probe.start_child = lambda: recovered.start(user_id, "one_llm_call", {})
    assert await recovered.recover_on_startup() == [parent]
    await wait_idle(recovered, parent)
    assert (await get_session(db_factory, user_id, parent)).status == "completed"
    child = probe.child_id
    second = await step(recovered, db_factory, user_id, child)
    assert second != first
    results = await asyncio.gather(
        *(recovered.submit_step(user_id, child, second, "Réponse suivante.") for _ in range(2)),
        return_exceptions=True,
    )
    assert results.count(None) == 1
    assert [err.code for err in results if isinstance(err, AppError)] == ["stale_interrupt"]
    await wait_idle(recovered, child)
    assert (await get_session(db_factory, user_id, child)).status == "completed"
    assert await _calls(db_factory, parent) == await _calls(db_factory, child) == 1
