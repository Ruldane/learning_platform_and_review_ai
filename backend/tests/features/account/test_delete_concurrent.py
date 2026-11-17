"""« Tout supprimer » face aux sessions qui naissent pendant la suppression : aucune ne survit au
compte (garde par compte du runner, annulation reprise en boucle)."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graphs.registry import GRAPHS, GraphSpec
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.runner import ACCOUNT_DELETING_CODE, SessionRunner
from app.core.errors import AppError
from app.db.models.agents import AgentSession
from tests.agents.graphs_for_tests import TEST_GRAPHS, NoInput, State
from tests.support.account_delete import (
    delete_account,
    has_checkpoint,
    me_of,
    row_counts,
    saver_of,
    seed_footprint,
)


def _runner(app: FastAPI) -> SessionRunner:
    runner: SessionRunner = app.state.runtime.runner
    return runner


async def _until(done: Callable[[], bool]) -> None:
    async with asyncio.timeout(10):
        while not done():
            await asyncio.sleep(0.01)


async def test_a_session_that_starts_another_during_the_cancellation_leaves_nothing(
    client: httpx.AsyncClient,
    app: FastAPI,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    me, runner = me_of(app), _runner(app)
    started, release = asyncio.Event(), asyncio.Event()
    launched: list[str] = []  # l'id de la fille si elle a démarré, sinon le code du refus

    def spawner(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
        async def spawn(state: State) -> State:
            started.set()
            await release.wait()
            try:
                launched.append(await runner.start(me, "two_steps", {}))
            except AppError as exc:
                launched.append(exc.code)
            return {}

        graph = StateGraph(State)
        graph.add_node("spawn", spawn)
        graph.add_edge(START, "spawn")
        graph.add_edge("spawn", END)
        return graph

    monkeypatch.setitem(GRAPHS, "spawner", GraphSpec("spawner", NoInput, spawner))
    monkeypatch.setitem(GRAPHS, "two_steps", TEST_GRAPHS["two_steps"])
    parent = await runner.start(me, "spawner", {})
    await asyncio.wait_for(started.wait(), 10)
    real_cancel = runner.cancel

    async def let_the_parent_spawn(user_id: str, session_id: str) -> AgentSession:
        release.set()  # la lanceuse finit pendant la boucle d'annulation
        await _until(lambda: bool(launched))
        return await real_cancel(user_id, session_id)

    monkeypatch.setattr(runner, "cancel", let_the_parent_spawn)

    assert (await delete_account(client)).status_code == 204

    assert launched == [ACCOUNT_DELETING_CODE]  # la fille n'a pas pu naître
    assert (await row_counts(db_session, me))["sessions"] == 0
    assert not await has_checkpoint(saver_of(app), parent)


async def test_the_cancellation_loops_until_no_session_is_left_open(
    client: httpx.AsyncClient,
    app: FastAPI,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    me, runner = me_of(app), _runner(app)
    first = await seed_footprint(db_session, app, me, "moi", statuses=("running",))
    late = AgentSession(user_id=me, graph="demo_debate", status="running", input={})
    cancelled: list[str] = []
    real_cancel = runner.cancel

    async def a_session_appears(user_id: str, session_id: str) -> AgentSession:
        if not cancelled:  # née pendant la boucle, absente de la première lecture
            db_session.add(late)
            await db_session.commit()
        cancelled.append(session_id)
        return await real_cancel(user_id, session_id)

    monkeypatch.setattr(runner, "cancel", a_session_appears)

    assert (await delete_account(client)).status_code == 204

    assert cancelled == [first.threads[0], late.id]
    assert (await row_counts(db_session, me))["sessions"] == 0


@pytest.mark.parametrize("step", ["index", "storage"])
async def test_a_session_started_while_vectors_or_files_go_is_refused(
    client: httpx.AsyncClient,
    app: FastAPI,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    step: str,
) -> None:
    me, runner = me_of(app), _runner(app)
    await seed_footprint(db_session, app, me, "moi")
    monkeypatch.setitem(GRAPHS, "two_steps", TEST_GRAPHS["two_steps"])
    port = getattr(app.state.memory_providers, step)
    real: Callable[[str], Awaitable[Any]] = port.delete_user
    attempts: list[str] = []

    async def start_then_delete(user_id: str) -> Any:
        try:
            attempts.append(await runner.start(user_id, "two_steps", {}))
        except AppError as exc:  # le planificateur, un autre onglet
            attempts.append(exc.code)
        return await real(user_id)

    monkeypatch.setattr(port, "delete_user", start_then_delete)

    assert (await delete_account(client)).status_code == 204

    assert attempts == [ACCOUNT_DELETING_CODE]
    assert {n: c for n, c in (await row_counts(db_session, me)).items() if c} == {"users": 1}


async def test_the_guard_is_lifted_after_a_failed_delete(
    client: httpx.AsyncClient,
    app: FastAPI,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    me, runner = me_of(app), _runner(app)
    await seed_footprint(db_session, app, me, "moi")
    monkeypatch.setitem(GRAPHS, "two_steps", TEST_GRAPHS["two_steps"])

    async def boom(session_ids: list[str]) -> None:
        raise RuntimeError("panne")

    monkeypatch.setattr(runner, "delete_threads", boom)
    assert (await delete_account(client)).status_code == 500

    assert await runner.start(me, "two_steps", {})  # le compte vit encore : il peut travailler
