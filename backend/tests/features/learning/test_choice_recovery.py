"""Reprise manquée et objectif orphelin (relecture 4.6, Important 1 et Minor 3) : un choix resté
écrit ne bloque jamais le Conseil qui attend ; un Conseil qui ne démarre pas ne laisse aucun
objectif."""

from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import update

from app.db.models.learning import Proposal
from app.features.learning.service import choice
from tests.features.learning.conftest import (
    GOALS,
    Stub,
    Waiting,
    chosen_ids,
    count_sessions,
)
from tests.sessions_support import wait_status

CHOOSE = "/api/v1/proposals/{}/choose"


async def test_failed_resume_clears_choice_and_next_click_resumes(
    client: httpx.AsyncClient,
    council_waiting_choice: Waiting,
    stub: Stub,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    waiting = council_waiting_choice
    p1 = waiting.ids[0]

    real, calls = choice._resume, []

    async def locked_once(*args: Any, **kwargs: Any) -> Any:
        calls.append(1)
        if len(calls) == 1:  # erreur hors AppError, après le commit du choix
            raise RuntimeError("database is locked")
        return await real(*args, **kwargs)

    monkeypatch.setattr(choice, "_resume", locked_once)
    r = await client.post(CHOOSE.format(p1), json={})
    assert r.status_code == 500
    assert await chosen_ids(client, waiting.goal_id) == set()  # choix effacé
    view = (await client.get(f"/api/v1/sessions/{waiting.sid}")).json()
    assert view["status"] == "waiting_user"
    r = await client.post(CHOOSE.format(p1), json={})
    assert r.status_code == 202 and r.json()["already_chosen"] is False
    await wait_status(client, waiting.sid, "completed")
    assert await count_sessions(client, "program_builder") == 1
    assert await chosen_ids(client, waiting.goal_id) == {p1}


async def test_choice_left_written_never_blocks_a_waiting_council(
    client: httpx.AsyncClient, app: FastAPI, council_waiting_choice: Waiting, stub: Stub
) -> None:
    """Arrêt du back entre le commit du choix et la reprise : le choix reste écrit, le Conseil
    attend toujours ; le clic suivant sur la même proposition le reprend."""
    waiting = council_waiting_choice
    p1 = waiting.ids[0]
    async with app.state.session_factory() as db:
        await db.execute(update(Proposal).where(Proposal.id == p1).values(chosen=True))
        await db.commit()
    r = await client.post(CHOOSE.format(p1), json={})
    assert r.status_code == 202 and r.json()["already_chosen"] is False
    await wait_status(client, waiting.sid, "completed")
    assert stub.resumed == [{"action": "choose", "proposal_ids": [p1], "start_date": None}]
    assert await count_sessions(client, "program_builder") == 1


async def test_goal_is_removed_when_council_launch_fails(
    client: httpx.AsyncClient, app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def broken(*args: Any, **kwargs: Any) -> str:
        raise RuntimeError("base indisponible")

    monkeypatch.setattr(app.state.learning.launcher, "start", broken)
    r = await client.post(GOALS, json={"text": "Devenir AI product engineer"})
    assert r.status_code == 500
    assert (await client.get(GOALS)).json() == []
