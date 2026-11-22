from collections.abc import AsyncIterator

import httpx
import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI

from app.core.deps import CurrentUser, get_interface_user
from app.db.models.accounts import User
from tests.features.project_handoffs.support import SUBMISSION, seed_project, submit_new_version
from tests.sessions_support import act_as

API = "/api/v1/project-handoffs"
FIELDS = {
    "commands": "python -m pytest tests/test_catalogue.py",
    "limitations": "Le jeu de données est fictif.",
    "steps": "Ouvrir la liste.\nChercher un livre par son titre.",
}


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with (
        LifespanManager(app, startup_timeout=30),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as http,
    ):
        yield http


async def test_approves_exact_preview_and_exports_the_frozen_guide(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    project_id = await seed_project(app)
    source = await client.get(f"{API}/source/{project_id}")
    assert source.status_code == 200, source.text
    assert source.json()["description"] == SUBMISSION
    draft = FIELDS | {"project_id": project_id}
    preview = (await client.post(f"{API}/preview", json=draft)).json()
    accepted = draft | {"expected_digest": preview["digest"], "approved": True}
    assert (await client.get(API)).json() == []
    assert (await client.post(API, json=accepted | {"approved": False})).status_code == 422
    await submit_new_version(app, project_id)
    assert (await client.post(API, json=accepted)).status_code == 409

    revised = (await client.post(f"{API}/preview", json=draft)).json()
    assert revised["digest"] != preview["digest"]
    response = await client.post(API, json=accepted | {"expected_digest": revised["digest"]})
    assert response.status_code == 201, response.text
    handoff = response.json()
    assert handoff["markdown"] == revised["markdown"]
    assert handoff["digest"] == revised["digest"]
    assert (await client.get(f"{API}/{handoff['id']}")).json() == handoff
    download = await client.get(f"{API}/{handoff['id']}/export")
    assert download.status_code == 200
    assert download.headers["cache-control"] == "private, no-store"
    assert download.headers["content-type"].startswith("text/markdown")
    assert download.content == revised["markdown"].encode()
    for value in FIELDS.values():
        assert all(line in download.text for line in value.splitlines())


async def test_guides_and_sources_belong_to_their_account(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    pending = await seed_project(app, submitted=False)
    assert (await client.get(f"{API}/source/{pending}")).status_code == 409
    project_id = await seed_project(app)
    draft = FIELDS | {"project_id": project_id}
    before = await client.post(f"{API}/preview", json=draft)
    assert before.status_code == 200, before.text
    accepted = draft | {"expected_digest": before.json()["digest"], "approved": True}
    created = await client.post(API, json=accepted)
    assert created.status_code == 201
    path = f"{API}/{created.json()['id']}"
    async with app.state.session_factory() as db:
        db.add(User(id="compte-transmission", user_id="compte-transmission"))
        await db.commit()
    act_as(app, "compte-transmission")
    app.dependency_overrides[get_interface_user] = lambda: CurrentUser("compte-transmission", None)
    assert (await client.get(f"{API}/source/{project_id}")).status_code == 404
    assert (await client.post(f"{API}/preview", json=draft)).status_code == 404
    assert (await client.post(API, json=accepted)).status_code == 404
    assert (await client.get(path)).status_code == 404
    assert (await client.get(f"{path}/export")).status_code == 404
    assert (await client.get(API)).json() == []
