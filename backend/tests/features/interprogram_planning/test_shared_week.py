from datetime import timedelta

import httpx
from fastapi import FastAPI

from app.db.models.program import Task
from tests.features.interprogram_planning.support import MONDAY, dates, seed_week

API = "/api/v1/interprogram-planning"


async def test_proposal_preserves_reserved_time_and_only_moves_tasks_after_acceptance(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    programs, tasks = await seed_week(app)
    options = await client.get(f"{API}/options")
    assert options.status_code == 200, options.text
    assert set(programs) <= {item["id"] for item in options.json()}
    selection = {"week_start": MONDAY.isoformat(), "program_ids": programs}
    proposal = await client.post(API, json=selection)
    assert proposal.status_code == 201, proposal.text
    preview = proposal.json()
    assert preview["status"] == "pending"
    assert await dates(app, tasks) == [MONDAY, MONDAY, MONDAY]
    assert preview["days"][0]["reserved_minutes"] == 30
    assert preview["days"][0]["capacity_minutes"] == 60
    assert preview["planned_minutes"] <= preview["cap_minutes"]
    assert [entry["task_id"] for entry in preview["placements"]] == tasks[:2]
    tuesday, wednesday = [MONDAY + timedelta(days=offset) for offset in (1, 2)]
    assert [entry["planned_date"] for entry in preview["placements"]] == [
        tuesday.isoformat(),
        wednesday.isoformat(),
    ]
    assert preview["prerequisites"][0]["status"] == "planned"
    path = f"{API}/{preview['id']}/accept"
    assert (await client.post(path, json={"confirmed": False})).status_code == 422
    accepted = await client.post(path, json={"confirmed": True})
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "accepted"
    assert await dates(app, tasks) == [tuesday, wednesday, MONDAY]
    assert (await client.post(path, json={"confirmed": True})).json() == accepted.json()
    assert (await client.get(API)).json()[0] == accepted.json()


async def test_acceptance_rejects_a_changed_source_without_partial_updates(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    programs, tasks = await seed_week(app)
    proposal = await client.post(
        API, json={"week_start": MONDAY.isoformat(), "program_ids": programs}
    )
    assert proposal.status_code == 201
    manual_day = MONDAY + timedelta(days=3)
    async with app.state.session_factory() as db:
        fixed = await db.get(Task, tasks[2])
        assert fixed is not None
        fixed.planned_date = manual_day
        await db.commit()
    response = await client.post(f"{API}/{proposal.json()['id']}/accept", json={"confirmed": True})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "shared_week_changed"
    assert await dates(app, tasks) == [MONDAY, MONDAY, manual_day]


async def test_combined_cap_blocks_the_week_without_moving_existing_tasks(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    programs, tasks = await seed_week(app)
    response = await client.get("/api/v1/settings")
    settings = response.json()
    settings["availability"] = {
        "weekday_minutes": 0,
        "weekend_block_min_minutes": 0,
        "weekend_block_max_minutes": 60,
    }
    saved = await client.put("/api/v1/settings", json=settings)
    assert saved.status_code == 200, saved.text
    result = await client.post(
        API, json={"week_start": MONDAY.isoformat(), "program_ids": programs}
    )
    assert result.status_code == 201
    blocked = result.json()
    assert blocked["status"] == "blocked" and blocked["cap_minutes"] == 51
    assert "weekly_budget" in blocked["issues"]
    rejected = await client.post(f"{API}/{blocked['id']}/accept", json={"confirmed": True})
    assert rejected.status_code == 409
    assert await dates(app, tasks) == [MONDAY] * 3
