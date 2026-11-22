from datetime import UTC, datetime, time, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx
from fastapi import FastAPI

ROOT = "/api/v1/routines"


async def _create(client: httpx.AsyncClient, hour: str) -> str:
    created = await client.post(ROOT, json={"action": "due_reviews", "local_time": hour})
    assert created.status_code == 201, created.text
    return str(created.json()["id"])


async def test_manual_execution_receipt_and_pause(client: httpx.AsyncClient) -> None:
    routine = await _create(client, "08:30")
    receipt = str(uuid4())
    executions = f"{ROOT}/{routine}/executions"
    first = await client.post(executions, json={"receipt": receipt})
    replay = await client.post(executions, json={"receipt": receipt})
    assert first.status_code == replay.status_code == 201
    assert first.json() == replay.json()
    assert first.json()["result_count"] == 0
    paused = await client.patch(f"{ROOT}/{routine}", json={"enabled": False})
    assert paused.status_code == 200 and paused.json()["enabled"] is False
    assert (await client.get(executions)).json() == [first.json()]


async def test_daily_scheduler_uses_the_local_hour_and_executes_only_once(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    routine = await _create(client, "10:30")
    from app.features.routines.service import run_daily

    owner = app.state.local_user_id
    factory = app.state.session_factory
    paris = ZoneInfo("Europe/Paris")
    tomorrow = datetime.now(paris).date() + timedelta(days=1)
    due = datetime.combine(tomorrow, time(10, 31), paris).astimezone(UTC)
    early = due - timedelta(minutes=2)
    async with factory() as db:
        assert await run_daily(db, owner, early) == 0
        assert await run_daily(db, owner, due) == 1
        assert await run_daily(db, owner, due) == 0
    history = (await client.get(f"{ROOT}/{routine}/executions")).json()
    assert len(history) == 1 and history[0]["source"] == "scheduled"
