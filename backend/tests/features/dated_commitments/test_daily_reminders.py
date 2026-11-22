from datetime import UTC, datetime, timedelta

import httpx
from fastapi import FastAPI
from pytest import MonkeyPatch

from app.features.dated_commitments import service
from app.features.routines.service import run_daily
from tests.features.dated_commitments.test_dated_commitments import API, commitment


async def test_next_morning_keeps_the_observed_gap_among_five_notices(
    app: FastAPI, client: httpx.AsyncClient, monkeypatch: MonkeyPatch
) -> None:
    routine = await client.post(
        "/api/v1/routines", json={"action": "due_commitments", "local_time": "08:00"}
    )
    assert routine.status_code == 201, routine.text
    history = f"/api/v1/routines/{routine.json()['id']}/executions"

    morning = datetime(2030, 1, 8, 8, tzinfo=UTC)
    now = morning
    monkeypatch.setattr(service, "utcnow", lambda: now)
    item = await client.post(API, json={**commitment(), "due_on": "2030-01-07"})
    assert item.status_code == 201, item.text
    item_id = item.json()["id"]
    for _ in range(5):
        other = await client.post(API, json=commitment())
        assert other.status_code == 201, other.text

    owner = app.state.local_user_id
    async with app.state.session_factory() as db:
        assert await run_daily(db, owner, morning) == 1
    first = (await client.get(history)).json()[0]["notices"]
    assert len(first) == 5 and any(row["id"] == item_id and row["delta"] is None for row in first)

    now += timedelta(hours=4)
    measured = await client.post(f"{API}/{item_id}/review", json={"observed": "3.50"})
    assert measured.status_code == 200, measured.text
    async with app.state.session_factory() as db:
        assert await run_daily(db, owner, now) == 0
        assert await run_daily(db, owner, morning + timedelta(days=1)) == 1
    following = (await client.get(history)).json()[0]["notices"]
    assert len(following) == 5
    assert next((row["delta"] for row in following if row["id"] == item_id), None) == "-0.75"
