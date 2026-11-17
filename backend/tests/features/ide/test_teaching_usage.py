"""Consommation, préférences et accès du professeur (10.A3) : jetons de la séance et du jour,
préférences (mode, style, plafonds), isolation entre utilisatrices, lancement des exercices."""

from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from tests.features.ide.conftest import OTHER
from tests.features.ide.support import API, FILES, code, new_session
from tests.features.ide.teach_support import (
    MAIN,
    ScriptedModels,
    add_teacher_tokens,
    teach,
)
from tests.sessions_support import act_as

pytestmark = pytest.mark.usefixtures("me")


@pytest.fixture
async def session(client: httpx.AsyncClient) -> dict[str, Any]:
    return await new_session(client, {"main.py": MAIN, "test_main.py": FILES["test_main.py"]})


async def test_usage_sums_session_and_day_tokens(
    app: FastAPI, client: httpx.AsyncClient, session: dict[str, Any]
) -> None:
    sid = session["id"]
    other = await new_session(client)
    await add_teacher_tokens(app, sid, 600)
    await add_teacher_tokens(app, sid, 400)
    await add_teacher_tokens(app, other["id"], 1_000)
    await add_teacher_tokens(app, sid, 9_999, age_days=2)  # un autre jour : hors du jour
    usage = (await client.get(f"{API}/usage", params={"session_id": sid})).json()
    assert usage == {
        "session_tokens": 10_999,
        "day_tokens": 2_000,
        "session_cap": 100_000,
        "day_cap": 300_000,
        "mode_on_demand": False,
    }
    none = (await client.get(f"{API}/usage")).json()
    assert none["session_tokens"] == 0 and none["day_tokens"] == 2_000


async def test_preferences_round_trip_and_style(client: httpx.AsyncClient) -> None:
    default = (await client.get(f"{API}/preferences")).json()
    assert default["teacher_style"] == "guide" and default["teacher_mode"] == "auto"
    body = {
        "teacher_mode": "on_demand",
        "teacher_style": "pair",
        "idle_trigger": True,
        "mcp_can_write_files": True,
        "session_cap": 5_000,
        "day_cap": 20_000,
    }
    assert (await client.put(f"{API}/preferences", json=body)).json() == body
    assert (await client.put(f"{API}/preferences", json={**body, "session_cap": 6_000})).json()[
        "session_cap"
    ] == 6_000
    assert (await client.get(f"{API}/preferences")).json()["session_cap"] == 6_000
    bad = await client.put(f"{API}/preferences", json={**body, "teacher_style": "autre"})
    assert bad.status_code == 422


async def test_teach_is_scoped_to_the_user(
    app: FastAPI, client: httpx.AsyncClient, session: dict[str, Any], models: ScriptedModels
) -> None:
    act_as(app, OTHER)
    assert code(await teach(client, session["id"], "hint")) == "session_not_found"
    assert (
        await client.get(f"{API}/usage", params={"session_id": session["id"]})
    ).status_code == 404
    assert models.calls == []


async def test_unknown_run_is_404(
    client: httpx.AsyncClient, session: dict[str, Any], models: ScriptedModels
) -> None:
    sent = await teach(client, session["id"], "run_error", run_id="inconnue")
    assert code(sent) == "run_not_found" and models.calls == []


async def test_generate_starts_the_exercise_graph(
    client: httpx.AsyncClient, models: ScriptedModels
) -> None:
    sent = await client.post(f"{API}/exercises/generate", json={"topic": "les boucles"})
    assert sent.status_code == 202 and sent.json()["session_id"]  # le graphe : tests/agents/ide
