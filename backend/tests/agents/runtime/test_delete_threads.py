"""`delete_threads` : les points de reprise des sessions d'une utilisatrice, et eux seuls."""

from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver, empty_checkpoint
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.checkpointer import thread_config
from app.agents.runtime.handle import AgentRuntime
from app.agents.runtime.runner import SessionRunner
from tests.agents.runtime.runner_helpers import wait_idle, wait_status

type Factory = async_sessionmaker[AsyncSession]


async def _put(saver: BaseCheckpointSaver[Any], thread: str) -> None:
    metadata: Any = {"source": "input", "step": 0, "parents": {}}
    config = thread_config(thread)
    config["configurable"]["checkpoint_ns"] = ""  # le saver le demande à l'écriture
    config = await saver.aput(config, empty_checkpoint(), metadata, {})
    await saver.aput_writes(config, [("canal", "valeur")], "tache-1")


async def _has(saver: BaseCheckpointSaver[Any], thread: str) -> bool:
    return await saver.aget_tuple(thread_config(thread)) is not None


async def test_delete_threads_removes_only_the_given_threads(
    runner: SessionRunner, checkpointer: BaseCheckpointSaver[Any]
) -> None:
    for thread in ("s1", "s2", "s3"):
        await _put(checkpointer, thread)

    await runner.delete_threads(["s1", "s2"])

    assert not await _has(checkpointer, "s1") and not await _has(checkpointer, "s2")
    assert await _has(checkpointer, "s3")
    kept = await checkpointer.aget_tuple(thread_config("s3"))
    assert kept is not None and kept.pending_writes  # ses écritures en attente restent aussi


async def test_delete_threads_is_idempotent_and_accepts_nothing(
    runner: SessionRunner, checkpointer: BaseCheckpointSaver[Any]
) -> None:
    await _put(checkpointer, "s1")
    await runner.delete_threads([])
    await runner.delete_threads(["inconnu", "s1"])
    await runner.delete_threads(["s1"])  # déjà effacé : rien à dire
    assert not await _has(checkpointer, "s1")


async def test_delete_threads_removes_the_checkpoints_of_a_finished_session(
    runner: SessionRunner,
    checkpointer: BaseCheckpointSaver[Any],
    db_factory: Factory,
    user_id: str,
) -> None:
    sid = await runner.start(user_id, "two_steps", {})
    await wait_status(db_factory, user_id, sid, "completed")
    await wait_idle(runner, sid)
    assert await _has(checkpointer, sid)

    await runner.delete_threads([sid])

    assert not await _has(checkpointer, sid)


async def test_the_runtime_handle_delegates_to_its_runner(
    runner: SessionRunner, checkpointer: BaseCheckpointSaver[Any]
) -> None:
    await _put(checkpointer, "s1")
    handle = AgentRuntime(bus=runner._bus, runner=runner)

    await handle.delete_threads(["s1"])

    assert not await _has(checkpointer, "s1")
