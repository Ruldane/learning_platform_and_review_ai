from datetime import datetime, timedelta

import httpx
from fastapi import FastAPI

from app.db.base import utcnow
from app.features.missions.service import MissionRuntime
from tests.features.missions.support import ARTIFACT, FIRST, SECOND, seed_posting

API = "/api/v1/missions"


async def test_mission_snapshots_requirements_and_replays_progress_and_private_evidence(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    posting = await seed_posting(app)
    start = {"posting_id": posting, "requirement_indices": [0, 1]}
    launched = await client.post(API, json=start)
    assert launched.status_code == 201, launched.text
    mission = launched.json()
    path = f"{API}/{mission['id']}"
    assert mission["posting_id"] == posting
    assert [criterion["text"] for criterion in mission["criteria"]] == [FIRST, SECOND]
    assert all(criterion["target"] == 2 for criterion in mission["criteria"])
    assert datetime.fromisoformat(mission["deadline_at"]) - datetime.fromisoformat(
        mission["created_at"]
    ) == timedelta(hours=48)
    assert (await client.post(API, json=start)).json() == mission
    await progress_and_submit(client, path)


async def progress_and_submit(client: httpx.AsyncClient, path: str) -> None:
    partial = {"revision": 0, "observed": 1, "note": "Le cas nominal est mesuré."}
    saved = await client.patch(f"{path}/criteria/0", json=partial)
    assert saved.status_code == 200
    draft = saved.json()
    assert draft["criteria"][0]["level"] == "in_progress"
    assert draft["revision"] == 1
    assert (await client.patch(f"{path}/criteria/0", json=partial)).json() == draft
    assert (await client.get(path)).json() == draft
    stale = await client.patch(f"{path}/criteria/1", json={"revision": 0, "observed": 2})
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "mission_changed"
    record = {"revision": 1, "artifact": ARTIFACT}
    early = await client.post(f"{path}/submission", json=record)
    assert early.status_code == 409 and early.json()["error"]["code"] == "mission_incomplete"
    for index in (0, 1):
        action = {"revision": 1 + index, "observed": 2}
        result = await client.patch(f"{path}/criteria/{index}", json=action)
        assert result.status_code == 200
        assert result.json()["criteria"][index]["level"] == "achieved"
    submitted = await client.post(f"{path}/submission", json={**record, "revision": 3})
    assert submitted.status_code == 200, submitted.text
    finished = submitted.json()
    assert finished["status"] == "completed"
    assert finished["submission"]["artifact"] == ARTIFACT
    assert finished["criteria"][0]["note"] == partial["note"]
    assert finished["submission"]["proof_id"]
    assert (
        await client.post(f"{path}/submission", json={**record, "revision": 3})
    ).json() == finished
    assert (await client.get(path)).json() == finished
    assert (await client.get(API)).json() == [finished]


async def test_mission_refuses_unanalysed_or_unknown_requirements(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    draft = await seed_posting(app, ready=False)
    response = await client.post(API, json={"posting_id": draft, "requirement_indices": [0]})
    assert response.status_code == 409
    posting = await seed_posting(app)
    for invalid in ([2], [0, 0]):
        response = await client.post(
            API, json={"posting_id": posting, "requirement_indices": invalid}
        )
        assert response.status_code == 422
    assert (await client.get(API)).json() == []


async def test_mission_is_readable_at_the_deadline_but_refuses_changes(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    now = utcnow()
    runtime = MissionRuntime(app.state.session_factory, now=lambda: now)
    app.state.missions = runtime
    posting = await seed_posting(app)
    result = await client.post(API, json={"posting_id": posting, "requirement_indices": [0]})
    assert result.status_code == 201
    path = f"{API}/{result.json()['id']}"
    now += timedelta(hours=48)
    assert (await client.get(path)).json()["status"] == "expired"
    late = await client.patch(f"{path}/criteria/0", json={"revision": 0, "observed": 1})
    assert late.status_code == 409 and late.json()["error"]["code"] == "mission_expired"
