"""`POST /account/delete` : les sessions en cours annulées avant, la reprise après une panne et
le verrou partagé avec l'export."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graphs.registry import GRAPHS
from app.db.models.agents import AgentSession
from app.features.account.service import export_lock
from app.providers.vector.base import VectorStoreUnavailable
from tests.agents.graphs_for_tests import TEST_GRAPHS, reset_probe
from tests.support.account import OTHER, export_archive, seed_other_user
from tests.support.account_delete import (
    delete_account,
    goals_of,
    has_checkpoint,
    me_of,
    row_counts,
    saver_of,
    seed_footprint,
    vector_count,
)

# --- Les sessions en cours -----------------------------------------------------------------------


async def test_delete_cancels_running_sessions(
    client: httpx.AsyncClient,
    app: FastAPI,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    me = me_of(app)
    await seed_other_user(db_session)
    mine = await seed_footprint(
        db_session, app, me, "moi", statuses=("waiting_user", "paused", "completed", "failed")
    )
    theirs = await seed_footprint(db_session, app, OTHER, "autre", statuses=("running",))
    probe = reset_probe()
    monkeypatch.setitem(GRAPHS, "blocking", TEST_GRAPHS["blocking"])
    runner = app.state.runtime.runner
    running = await runner.start(me, "blocking", {})  # une vraie tâche, bloquée dans son nœud
    await asyncio.wait_for(probe.b_started.wait(), 10)
    cancelled: list[tuple[str, str]] = []
    real_cancel = runner.cancel

    async def spy(user_id: str, session_id: str) -> Any:
        cancelled.append((user_id, session_id))
        return await real_cancel(user_id, session_id)

    monkeypatch.setattr(runner, "cancel", spy)

    assert (await delete_account(client)).status_code == 204

    assert not runner.is_active(running) and not probe.b_done.is_set()
    expected = {(me, running), (me, mine.threads[0]), (me, mine.threads[1])}
    assert set(cancelled) == expected  # ni les terminées, ni la session de l'autre compte
    assert not await has_checkpoint(saver_of(app), running)
    assert await db_session.get(AgentSession, theirs.threads[0]) is not None
    assert (await row_counts(db_session, me))["sessions"] == 0


async def test_a_session_finished_meanwhile_does_not_stop_the_delete(
    client: httpx.AsyncClient,
    app: FastAPI,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mine = await seed_footprint(db_session, app, me_of(app), "moi", statuses=("running",))
    runner = app.state.runtime.runner
    real_cancel = runner.cancel

    async def finished_first(user_id: str, session_id: str) -> Any:
        await real_cancel(user_id, session_id)  # une autre annulation est passée avant
        return await real_cancel(user_id, session_id)  # 409 : déjà terminée

    monkeypatch.setattr(runner, "cancel", finished_first)
    assert (await delete_account(client)).status_code == 204
    assert not await has_checkpoint(saver_of(app), mine.threads[0])


# --- Qdrant en panne, puis la reprise -----------------------------------------------------------


async def test_delete_vector_down_then_retry_completes(
    client: httpx.AsyncClient,
    app: FastAPI,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    me = me_of(app)
    mine = await seed_footprint(db_session, app, me, "moi", statuses=("running",))
    index = app.state.memory_providers.index
    real: Callable[[str], Awaitable[None]] = index.delete_user
    calls: list[str] = []

    async def down_once(user_id: str) -> None:
        calls.append(user_id)
        if len(calls) == 1:
            raise VectorStoreUnavailable()
        await real(user_id)

    monkeypatch.setattr(index, "delete_user", down_once)

    failed = await delete_account(client)

    assert failed.status_code == 503
    assert failed.json()["error"]["code"] == "vector_store_unavailable"
    counts = await row_counts(db_session, me)  # rien n'est supprimé en base
    assert counts["goals"] == 1 and counts["api_keys"] == 1 and counts["sessions"] == 1
    assert await app.state.memory_providers.storage.list_user(me) == mine.files

    assert (await delete_account(client)).status_code == 204  # un nouvel appel reprend
    assert calls == [me, me]
    assert {n: c for n, c in (await row_counts(db_session, me)).items() if c} == {"users": 1}
    assert await vector_count(app, me) == 0
    assert not await has_checkpoint(saver_of(app), mine.threads[0])


async def test_delete_interrupted_after_the_files_is_replayed(
    client: httpx.AsyncClient,
    app: FastAPI,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    me = me_of(app)
    mine = await seed_footprint(db_session, app, me, "moi")
    runner = app.state.runtime.runner
    real = runner.delete_threads

    async def boom(session_ids: list[str]) -> None:
        raise RuntimeError("le fichier des points de reprise est verrouillé")

    monkeypatch.setattr(runner, "delete_threads", boom)
    assert (await delete_account(client)).status_code == 500
    assert await goals_of(db_session, me) == 1  # la base n'est touchée qu'à la fin
    assert await app.state.memory_providers.storage.list_user(me) == []  # déjà effacés

    monkeypatch.setattr(runner, "delete_threads", real)
    assert (await delete_account(client)).status_code == 204
    assert await goals_of(db_session, me) == 0
    assert not await has_checkpoint(saver_of(app), mine.threads[0])


# --- Un export et une suppression ne se croisent pas ---------------------------------------------


async def test_delete_waits_for_a_running_export(
    client: httpx.AsyncClient, app: FastAPI, db_session: AsyncSession
) -> None:
    me = me_of(app)
    await seed_footprint(db_session, app, me, "moi")
    await export_archive(client)  # crée `app.state.account_locks`
    async with export_lock(app.state.account_locks, me):
        task = asyncio.create_task(delete_account(client))
        for _ in range(100):
            await asyncio.sleep(0)
        assert not task.done() and await goals_of(db_session, me) == 1
    assert (await task).status_code == 204
    assert await goals_of(db_session, me) == 0
