"""Le défi est rattaché au programme et reprend à l'heure du serveur."""

from datetime import UTC, datetime, timedelta

import httpx
from fastapi import FastAPI

from tests.support.boss import completed_program


async def test_reopening_keeps_the_clock_project_and_client_change(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    now = datetime(2026, 11, 22, 13, tzinfo=UTC)
    app.state.boss_clock = lambda: now
    program = await completed_program(app)
    route = f"/api/v1/boss/programs/{program}"
    before = await client.get(route)
    assert before.status_code == 200
    assert before.json()["eligible"] and before.json()["attempt"] is None

    opened = await client.post(route)
    assert opened.status_code == 201
    attempt = opened.json()
    assert attempt["client_change"] is None and attempt["state"] == "building"
    assert datetime.fromisoformat(attempt["deadline_at"]) == now + timedelta(minutes=30)
    assert (await client.post(f"{route}/submit")).json()["error"]["code"] == "boss_change_pending"
    project = await client.get(f"/api/v1/ide/sessions/{attempt['ide_session_id']}")
    assert project.status_code == 200 and "service.py" in project.json()["files"]

    now += timedelta(minutes=11)
    resumed = (await client.get(route)).json()["attempt"]
    assert resumed["client_change"]["requirement"]
    assert resumed["id"] == attempt["id"] and resumed["deadline_at"] == attempt["deadline_at"]
    assert (await client.post(route)).json()["client_change"] == resumed["client_change"]

    now += timedelta(minutes=20)
    assert (await client.get(route)).json()["attempt"]["state"] == "expired"
    refused = await client.post(f"{route}/submit")
    assert refused.status_code == 409 and refused.json()["error"]["code"] == "boss_expired"
