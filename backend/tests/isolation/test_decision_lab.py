from collections.abc import AsyncIterator

import httpx
import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI

from app.db.models.accounts import User
from tests.sessions_support import act_as

API = "/api/v1/decision-lab"
ARCHITECTURE = {"replicas": 1, "replica_capacity_rps": 100, "hourly_cost_cents": 10}
ASSUMPTIONS = {
    "request_rate": 200,
    "duration_minutes": 60,
    "outage_minutes": 10,
    "architecture_a": ARCHITECTURE,
    "architecture_b": {**ARCHITECTURE, "replicas": 2},
}


@pytest.fixture
async def lab_client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with (
        LifespanManager(app, startup_timeout=30.0),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client,
    ):
        yield client


async def test_scenarios_are_recalculated_and_scoped_to_the_account(
    app: FastAPI, lab_client: httpx.AsyncClient
) -> None:
    client = lab_client
    other = "autre-compte-laboratoire"
    async with app.state.session_factory() as db:
        db.add(User(id=other, user_id=other))
        await db.commit()
    comparison = await client.post(f"{API}/compare", json=ASSUMPTIONS)
    assert comparison.status_code == 200, comparison.text
    assert (await client.get(f"{API}/scenarios")).json() == []
    saved = await client.post(
        f"{API}/scenarios",
        json={"title": "Choix privé", "assumptions": ASSUMPTIONS, "critique": "Comparer le coût."},
    )
    assert saved.status_code == 201, saved.text
    scenario = saved.json()
    assert scenario["assumptions"] == ASSUMPTIONS
    assert scenario["results"] == comparison.json()
    assert scenario["critique"] == "Comparer le coût."
    path = f"{API}/scenarios/{scenario['id']}"
    assert (await client.get(path)).json() == scenario
    assert (await client.get(f"{API}/scenarios")).json()[0]["id"] == scenario["id"]

    act_as(app, other)
    assert (await client.get(f"{API}/scenarios")).json() == []
    assert (await client.get(path)).status_code == 404
    assert (await client.post(f"{API}/compare", json=ASSUMPTIONS)).json() == comparison.json()

    act_as(app, app.state.local_user_id)
    assert (await client.get(path)).json() == scenario


async def test_invalid_assumptions_are_refused_without_echo(lab_client: httpx.AsyncClient) -> None:
    client = lab_client
    invalid = {**ASSUMPTIONS, "outage_minutes": 61, "external": "Texte de test à ne pas renvoyer"}
    response = await client.post(f"{API}/compare", json=invalid)
    assert response.status_code == 422
    assert "Texte de test" not in response.text
    too_long = {**ASSUMPTIONS, "outage_minutes": 61}
    assert (await client.post(f"{API}/compare", json=too_long)).status_code == 422
