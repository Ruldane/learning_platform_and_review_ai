from fastapi import FastAPI

from tests.features.grade_appeals.support import CRITERION, REASON, seed_reviewed_project
from tests.isolation.conftest import Browser

API = "/api/v1/grade-appeals"


async def test_reviewed_material_and_appeals_are_private(
    google_app: FastAPI, google_client_factory: Browser
) -> None:
    owner = await google_client_factory("appeal-a@example.test")
    other = await google_client_factory("appeal-b@example.test")
    user_id = (await owner.get("/api/v1/auth/me")).json()["id"]
    project = await seed_reviewed_project(google_app, user_id)
    available = await owner.get(f"{API}/projects")
    assert available.status_code == 200
    assert [item["id"] for item in available.json()] == [project]
    assert (await other.get(f"{API}/projects")).json() == []
    source = f"{API}/projects/{project}/criteria"
    assert (await owner.get(source)).json()[0]["criterion"] == CRITERION
    assert (await other.get(source)).status_code == 404

    body = {"project_id": project, "criterion_index": 1, "reason": REASON}
    created = await owner.post(API, json=body)
    assert created.status_code == 201, created.text
    assert (await other.post(API, json=body)).status_code == 404
    assert (await other.get(API)).json() == []
    path = f"{API}/{created.json()['id']}"
    assert (await other.get(path)).status_code == 404
    assert (await other.post(f"{path}/review")).status_code == 404
    decision = {"decision": "accept_second"}
    assert (await other.post(f"{path}/decision", json=decision)).status_code == 404
    assert (await owner.post(f"{path}/decision", json=decision)).status_code == 409
