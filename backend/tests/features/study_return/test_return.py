from datetime import timedelta

import httpx
from fastapi import FastAPI

from app.db.base import utcnow
from tests.features.interprogram_planning.support import MONDAY, dates
from tests.features.study_return.support import ACQUIRED, ANSWER, DUE, seed_return

API = "/api/v1/study-return"


async def test_short_return_uses_owned_evidence_and_preserves_the_existing_schedule(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    block_id, task_id = await seed_return(app)
    initial = await client.get(API)
    assert initial.status_code == 200, initial.text
    assert initial.json() == {"plan": None, "reminder_on": None, "reminder_due": False}

    prepared = await client.post(f"{API}/prepare")
    assert prepared.status_code == 200, prepared.text
    plan = prepared.json()["plan"]
    assert 0 < plan["minutes"] <= 15
    assert [skill["name"] for skill in plan["skills"]] == [ACQUIRED]
    assert [card["front"] for card in plan["cards"]] == [DUE]
    assert ANSWER not in prepared.text
    assert plan["last_block"]["id"] == block_id and plan["last_block"]["minutes"] == 14
    assert (await client.get(API)).json() == prepared.json()

    started = await client.post(f"{API}/start")
    assert started.status_code == 200, started.text
    linked = started.json()["plan"]
    assert linked["training_id"] and linked["last_block"]["id"] == block_id
    training = await client.get(f"/api/v1/study-sessions/training/{linked['training_id']}")
    assert training.status_code == 200 and training.json()["mode"] == "direct"
    assert (await client.post(f"{API}/start")).json() == started.json()
    assert await dates(app, [task_id]) == [MONDAY]


async def test_reminder_stays_local_and_clears_only_on_start(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    today = utcnow().date()
    tomorrow = today + timedelta(days=2)
    future = await client.put(f"{API}/reminder", json={"day": tomorrow.isoformat()})
    assert future.status_code == 200 and future.json()["reminder_due"] is False
    from_yesterday = today - timedelta(days=1)
    due = await client.put(f"{API}/reminder", json={"day": from_yesterday.isoformat()})
    assert due.status_code == 200 and due.json()["reminder_due"] is True
    assert (await client.get(API)).json() == due.json()
    assert (await client.post(f"{API}/start")).status_code == 409
    assert (await client.get(API)).json()["reminder_due"] is True
    await client.post(f"{API}/prepare")
    started = await client.post(f"{API}/start")
    assert started.status_code == 200 and started.json()["reminder_on"] is None
