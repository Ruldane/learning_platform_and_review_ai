from collections.abc import AsyncIterator
from hashlib import sha256
from typing import Any
from uuid import uuid4

import httpx
import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI

from app.core.deps import CurrentUser, get_interface_user
from app.db.models.accounts import User
from tests.features.missions.support import seed_posting
from tests.sessions_support import act_as

API = "/api/v1"
PACKETS = f"{API}/proof-packets"
ARTIFACT = "Vérification écrite des mesures du prototype fictif."


@pytest.fixture
async def packets_client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with (
        LifespanManager(app, startup_timeout=30.0),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client,
    ):
        yield client


async def _mission(app: FastAPI, client: httpx.AsyncClient) -> str:
    posting = await seed_posting(app)
    created = await client.post(
        f"{API}/missions", json={"posting_id": posting, "requirement_indices": [0]}
    )
    assert created.status_code == 201, created.text
    return str(created.json()["id"])


async def _approve(client: httpx.AsyncClient, mission_id: str) -> dict[str, Any]:
    path = f"{API}/missions/{mission_id}"
    measured = await client.patch(f"{path}/criteria/0", json={"revision": 0, "observed": 2})
    assert measured.status_code == 200, measured.text
    approved = await client.post(f"{path}/submission", json={"revision": 1, "artifact": ARTIFACT})
    assert approved.status_code == 200, approved.text
    return {
        "mission_id": mission_id,
        "proof_id": approved.json()["submission"]["proof_id"],
        "revision": approved.json()["revision"],
    }


async def test_exports_only_approved_proofs_and_keeps_a_reproducible_snapshot(
    app: FastAPI, packets_client: httpx.AsyncClient
) -> None:
    client = packets_client
    mission_id = await _mission(app, client)
    sources = await client.get(f"{PACKETS}/sources")
    assert sources.status_code == 200 and sources.json() == []
    prompt = {
        "title": "Vérifier la preuve",
        "sources": [{"mission_id": mission_id, "proof_id": str(uuid4()), "revision": 0}],
    }
    assert (await client.post(f"{PACKETS}/preview", json=prompt)).status_code == 409

    source = await _approve(client, mission_id)
    prompt["sources"] = [source]
    assert (await client.get(f"{PACKETS}/sources")).json()[0]["proof_id"] == source["proof_id"]
    preview = await client.post(f"{PACKETS}/preview", json=prompt)
    assert preview.status_code == 200, preview.text
    artifact = preview.json()["manifest"]["proofs"][0]
    assert artifact["revision"] == source["revision"]
    assert artifact["artifact"] == ARTIFACT
    assert artifact["artifact_digest"] == sha256(ARTIFACT.encode()).hexdigest()
    assert artifact["measurements"][0]["observed"] == artifact["measurements"][0]["target"] == 2
    assert preview.json()["manifest"]["procedure"]
    assert (await client.get(PACKETS)).json() == []

    changed = prompt | {"expected_digest": "0" * 64}
    assert (await client.post(PACKETS, json=changed)).status_code == 409
    saved = await client.post(PACKETS, json=prompt | {"expected_digest": preview.json()["digest"]})
    assert saved.status_code == 201, saved.text
    path = f"{PACKETS}/{saved.json()['id']}/export"
    first = await client.get(path)
    assert first.status_code == 200 and first.headers["cache-control"] == "private, no-store"
    assert first.json() == preview.json()["manifest"]
    assert sha256(first.content).hexdigest() == preview.json()["digest"]
    assert (await client.get(path)).content == first.content


async def test_sources_and_packets_are_scoped_to_the_account(
    app: FastAPI, packets_client: httpx.AsyncClient
) -> None:
    client = packets_client
    source = await _approve(client, await _mission(app, client))
    prompt = {"title": "Dossier privé", "sources": [source]}
    preview = await client.post(f"{PACKETS}/preview", json=prompt)
    assert preview.status_code == 200, preview.text
    body = prompt | {"expected_digest": preview.json()["digest"]}
    saved = await client.post(PACKETS, json=body)
    assert saved.status_code == 201, saved.text
    path = f"{PACKETS}/{saved.json()['id']}"

    other = "autre-compte-preuves"
    async with app.state.session_factory() as db:
        db.add(User(id=other, user_id=other))
        await db.commit()
    act_as(app, other)
    app.dependency_overrides[get_interface_user] = lambda: CurrentUser(other, None)
    assert (await client.get(f"{PACKETS}/sources")).json() == []
    assert (await client.post(f"{PACKETS}/preview", json=prompt)).status_code == 404
    assert (await client.post(PACKETS, json=body)).status_code == 404
    assert (await client.get(PACKETS)).json() == []
    assert (await client.get(path)).status_code == 404
    assert (await client.get(f"{path}/export")).status_code == 404

    act_as(app, app.state.local_user_id)
    app.dependency_overrides.pop(get_interface_user)
    assert (await client.get(path)).json() == saved.json()
