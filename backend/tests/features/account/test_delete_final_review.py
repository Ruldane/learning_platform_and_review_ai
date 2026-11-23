"""Revue finale 9.R, zone B : vecteurs rappelés après les lignes (B-I2), cinquième tour d'annulation
(m1), garde revérifiée par `start` (m2), disque verrouillé (m6)."""

import asyncio
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graphs.registry import GRAPHS
from app.agents.runtime import repositories
from app.agents.runtime.runner import ACCOUNT_DELETING_CODE, SessionRunner
from app.core.errors import AppError
from app.db.models.agents import AgentSession
from app.features.account.service.delete import ROUNDS
from tests.agents.graphs_for_tests import TEST_GRAPHS
from tests.support.account_delete import (
    delete_account,
    me_of,
    row_counts,
    seed_footprint,
    vector_count,
)
from tests.support.memory import make_chunk


async def test_a_vector_inserted_while_the_rows_go_is_removed_by_the_second_pass(
    client: httpx.AsyncClient,
    app: FastAPI,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Un `indexer.push` en vol qui finit après `delete_user` (avant la transaction des lignes) ne
    laisse rien dans l'index : `delete_user` est rappelé après les lignes."""
    me = me_of(app)
    await seed_footprint(db_session, app, me, "moi")
    index = app.state.memory_providers.index
    real = index.delete_user
    calls: list[int] = []

    async def delete_then_late_push(user_id: str) -> Any:
        result = await real(user_id)
        if not calls:  # le push en vol finit juste après le premier effacement
            await index.index([make_chunk(user_id, "texte du CV")])
        calls.append(1)
        return result

    monkeypatch.setattr(index, "delete_user", delete_then_late_push)

    assert (await delete_account(client)).status_code == 204

    assert len(calls) == 2
    assert await vector_count(app, me) == 0


async def test_the_second_vector_pass_failing_is_a_retryable_503(
    client: httpx.AsyncClient,
    app: FastAPI,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.providers.vector.base import VectorStoreUnavailable

    me = me_of(app)
    await seed_footprint(db_session, app, me, "moi")
    index = app.state.memory_providers.index
    real = index.delete_user
    calls: list[int] = []

    async def second_fails(user_id: str) -> Any:
        calls.append(1)
        if len(calls) == 2:
            raise VectorStoreUnavailable()
        return await real(user_id)

    monkeypatch.setattr(index, "delete_user", second_fails)
    response = await delete_account(client)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "vector_purge_incomplete"
    assert (await row_counts(db_session, me))["sessions"] == 0
    assert (await delete_account(client)).status_code == 204  # le rejeu finit le travail


async def test_a_session_that_never_closes_is_a_retryable_503_before_any_row_goes(
    client: httpx.AsyncClient,
    app: FastAPI,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    me = me_of(app)
    await seed_footprint(db_session, app, me, "moi")
    runner: SessionRunner = app.state.runtime.runner
    before = await row_counts(db_session, me)
    rounds: list[int] = []
    deleted: list[object] = []

    async def always_open(user_id: str) -> list[str]:
        rounds.append(1)
        return ["une-session"]

    async def cancelled(user_id: str, session_id: str) -> Any:
        return None

    async def spy(session_ids: Any) -> None:
        deleted.append(session_ids)

    monkeypatch.setattr(runner, "open_sessions", always_open)
    monkeypatch.setattr(runner, "cancel", cancelled)
    monkeypatch.setattr(runner, "delete_threads", spy)

    response = await delete_account(client)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "account_busy"
    assert len(rounds) == ROUNDS and deleted == []
    assert await row_counts(db_session, me) == before


async def test_start_rechecks_the_guard_after_its_commit(
    client: httpx.AsyncClient,
    app: FastAPI,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """La suppression commence entre le contrôle de `start` et son commit : la ligne née est
    annulée et rien ne démarre."""
    me = me_of(app)
    runner: SessionRunner = app.state.runtime.runner
    monkeypatch.setitem(GRAPHS, "two_steps", TEST_GRAPHS["two_steps"])
    real_add = repositories.SessionRepository.add

    async def add_then_delete_begins(self: Any, **values: Any) -> AgentSession:
        row: AgentSession = await real_add(self, **values)
        runner._deleting.add(me)  # « Tout supprimer » vient de commencer
        return row

    monkeypatch.setattr(repositories.SessionRepository, "add", add_then_delete_begins)

    with pytest.raises(AppError) as raised:
        await runner.start(me, "two_steps", {})
    assert raised.value.code == ACCOUNT_DELETING_CODE
    await asyncio.sleep(0)
    assert not runner._tasks  # aucune tâche lancée
    statuses = (await db_session.execute(select(AgentSession.status))).scalars().all()
    assert statuses and set(statuses) == {"cancelled"}


async def test_a_locked_folder_is_a_retryable_503_not_a_500(
    client: httpx.AsyncClient,
    app: FastAPI,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    me = me_of(app)
    await seed_footprint(db_session, app, me, "moi")
    before = await row_counts(db_session, me)
    storage = app.state.memory_providers.storage

    async def locked(user_id: str) -> int:
        raise PermissionError("[WinError 32] fichier ouvert ailleurs : C:/secret/chemin")

    monkeypatch.setattr(storage, "delete_user", locked)

    response = await delete_account(client)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "storage_unavailable"
    assert "secret" not in response.text and "WinError" not in response.text
    assert await row_counts(db_session, me) == before  # rien n'est supprimé en base
