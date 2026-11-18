"""Objectif écrit en direct (`POST /goals/direct`) : les champs de `POST /goals`, mais aucun
Conseil, aucune session, aucun appel au modèle."""

from datetime import date, timedelta
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from tests.features.learning.conftest import GOALS
from tests.sessions_support import act_as
from tests.support.direct import OTHER, assert_no_agent

DIRECT = f"{GOALS}/direct"
SECRET = "SECRET-DE-L-OBJECTIF"


def body() -> dict[str, Any]:
    return {
        "text": "  Les bases du ML pour l'ingénierie IA  ",
        "target_role": "AI engineer",
        "deadline": (date.today() + timedelta(days=90)).isoformat(),
        "weekly_hours": 7,
    }


async def test_direct_goal_is_written_without_council(
    client: httpx.AsyncClient, app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def refuse(*args: object, **kwargs: object) -> str:
        raise AssertionError("un graphe a été lancé")

    monkeypatch.setattr(app.state.learning.launcher, "start", refuse)

    r = await client.post(DIRECT, json=body())

    assert r.status_code == 201, r.text
    goal = r.json()
    assert goal["text"] == "Les bases du ML pour l'ingénierie IA"  # blancs autour retirés
    assert (goal["target_role"], goal["weekly_hours"]) == ("AI engineer", 7)
    assert goal["deadline"] == body()["deadline"]
    assert goal["status"] == "chosen"  # ni Conseil ni choix à faire : le programme se pose ensuite
    assert goal["council_session_id"] is None and goal["program_id"] is None
    assert [g["id"] for g in (await client.get(GOALS)).json()] == [goal["id"]]
    await assert_no_agent(app)


async def test_direct_goal_needs_only_the_text(client: httpx.AsyncClient, app: FastAPI) -> None:
    r = await client.post(DIRECT, json={"text": "Apprendre le SQL à fond"})

    assert r.status_code == 201, r.text
    assert (r.json()["deadline"], r.json()["weekly_hours"]) == (None, None)
    await assert_no_agent(app)


@pytest.mark.parametrize(
    "extra",
    [
        {"text": "abc"},
        {"text": "x" * 501},
        {"weekly_hours": 41},
        {"deadline": "2000-01-01"},
        {"target_role": ""},
    ],
)
async def test_direct_goal_422_without_echo(
    client: httpx.AsyncClient, app: FastAPI, extra: dict[str, Any]
) -> None:
    sent = {**body(), "text": f"{SECRET} un objectif", **extra}

    r = await client.post(DIRECT, json=sent)

    assert r.status_code == 422
    assert SECRET not in r.text and "2000-01-01" not in r.text
    assert (await client.get(GOALS)).json() == []
    await assert_no_agent(app)


async def test_direct_goal_is_private_to_its_owner(client: httpx.AsyncClient, app: FastAPI) -> None:
    mine = (await client.post(DIRECT, json=body())).json()["id"]

    act_as(app, OTHER)

    assert (await client.get(GOALS)).json() == []
    r = await client.get(f"{GOALS}/{mine}")
    assert r.status_code == 404 and r.json()["error"]["code"] == "goal_not_found"
