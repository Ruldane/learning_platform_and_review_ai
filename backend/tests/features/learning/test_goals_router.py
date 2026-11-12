"""Objectifs : création (lance le Conseil), lectures, isolation, propositions du dernier lot,
journaux sans texte saisi."""

import logging
from datetime import date, timedelta

import httpx
import pytest
from fastapi import FastAPI

from tests.features.learning.conftest import (
    GOALS,
    Stub,
    start_goal,
    wait_choice,
)
from tests.sessions_support import act_as, wait_status


async def test_create_goal_starts_council(client: httpx.AsyncClient) -> None:
    deadline = (date.today() + timedelta(days=90)).isoformat()
    body = {
        "text": "  Devenir AI product engineer  ",
        "target_role": "AI product engineer",
        "deadline": deadline,
        "weekly_hours": 10,
    }
    r = await client.post(GOALS, json=body)
    assert r.status_code == 201
    started = r.json()
    goal = started["goal"]
    assert goal["council_session_id"] == started["session_id"]
    assert goal["text"] == "Devenir AI product engineer"  # blancs autour retirés
    assert (goal["deadline"], goal["weekly_hours"], goal["status"]) == (deadline, 10, "council")
    assert goal["program_id"] is None and goal["program_session_id"] is None
    session = (await client.get(f"/api/v1/sessions/{started['session_id']}")).json()
    assert session["graph"] == "learning_council"
    assert (session["subject_type"], session["subject_id"]) == ("goal", goal["id"])


@pytest.mark.parametrize(
    "body",
    [
        {"text": "Devenir AI product engineer", "deadline": "2000-01-01"},
        {"text": "abc"},
        {"text": "Devenir AI product engineer", "weekly_hours": 41},
        {"text": "x" * 501},
    ],
)
async def test_goal_with_past_deadline_is_422_without_echo(
    client: httpx.AsyncClient, body: dict[str, object]
) -> None:
    r = await client.post(GOALS, json=body)
    assert r.status_code == 422
    assert str(body["text"]) not in r.text and "2000-01-01" not in r.text
    assert (await client.get(GOALS)).json() == []  # rien d'enregistré


async def test_goals_listed_recent_first_and_readable(client: httpx.AsyncClient) -> None:
    first, _ = await start_goal(client, "Premier objectif")
    second, _ = await start_goal(client, "Second objectif")
    listed = (await client.get(GOALS)).json()
    assert [g["id"] for g in listed] == [second, first]
    one = (await client.get(f"{GOALS}/{first}")).json()
    assert one["text"] == "Premier objectif"


async def test_goals_isolated_between_users(
    client: httpx.AsyncClient, app: FastAPI, stub: Stub
) -> None:
    waiting = await wait_choice(client)
    boards = (await client.get(f"{GOALS}/{waiting.goal_id}/boards")).json()
    act_as(app, "autre-utilisateur")
    assert (await client.get(GOALS)).json() == []
    for path in ["", "/proposals", "/boards"]:
        r = await client.get(f"{GOALS}/{waiting.goal_id}{path}")
        assert r.status_code == 404 and r.json()["error"]["code"] == "goal_not_found"
    r = await client.post(f"/api/v1/proposals/{waiting.ids[0]}/choose", json={})
    assert r.status_code == 404 and r.json()["error"]["code"] == "proposal_not_found"
    edit = {"scene": {"elements": []}, "note": "Intrusion"}
    r = await client.post(f"/api/v1/boards/{boards[0]['id']}/edits", json=edit)
    assert r.status_code == 404 and r.json()["error"]["code"] == "board_not_found"
    assert stub.resumed == []


async def test_proposals_route_returns_latest_batch(client: httpx.AsyncClient, stub: Stub) -> None:
    stub.batches = 2
    waiting = await wait_choice(client)
    rows = (await client.get(f"{GOALS}/{waiting.goal_id}/proposals")).json()
    assert [p["id"] for p in rows] == stub.batch_ids[2]
    assert [(p["batch"], p["rank"]) for p in rows] == [(2, 1), (2, 2), (2, 3)]
    first = rows[0]
    assert first["name"] == "Parcours 2.1" and first["skills"] == ["Python", "LLM"]
    assert first["chosen"] is False and first["board_id"] is None


async def test_routes_never_log_goal_text(
    client: httpx.AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG, logger="app")
    secret = "Objectif secret de January 7Q"
    waiting = await wait_choice(client, secret)
    boards = (await client.get(f"{GOALS}/{waiting.goal_id}/boards")).json()
    note = "Note secrète du tableau 9Z"
    edit = {"scene": {"elements": []}, "note": note}
    r = await client.post(f"/api/v1/boards/{boards[0]['id']}/edits", json=edit)
    assert r.status_code == 201
    r = await client.post(f"/api/v1/proposals/{waiting.ids[0]}/choose", json={})
    assert r.status_code == 202
    await wait_status(client, waiting.sid, "completed")
    logged = " | ".join(r.getMessage() for r in caplog.records if r.name.startswith("app"))
    assert waiting.goal_id in logged  # les routes journalisent bien (identifiants)
    assert secret not in logged and note not in logged and "Parcours 1.1" not in logged
