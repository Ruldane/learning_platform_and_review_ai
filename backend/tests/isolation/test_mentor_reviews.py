from collections.abc import AsyncIterator, Mapping
from datetime import timedelta
from uuid import uuid4

import httpx
import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI

from app.core.deps import CurrentUser, get_interface_user
from app.db.base import utcnow
from app.db.models.accounts import User
from tests.features.mentor_reviews.support import ARTIFACT, seed_packet
from tests.mcp.adapter_support import call
from tests.mcp.support import Mcp
from tests.sessions_support import act_as

API = "/api/v1/mentor-reviews"
SHARES = f"{API}/shares"
SHARED = f"{API}/shared"


@pytest.fixture
async def mentor_client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with (
        LifespanManager(app, startup_timeout=30.0),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost"
        ) as client,
    ):
        yield client


async def _assert_other_cannot_manage_share(
    app: FastAPI,
    client: httpx.AsyncClient,
    proposal: Mapping[str, object],
    path: str,
    comment_id: str,
) -> None:
    other = "autre-compte-mentor"
    async with app.state.session_factory() as db:
        db.add(User(id=other, user_id=other))
        await db.commit()
    act_as(app, other)
    app.dependency_overrides[get_interface_user] = lambda: CurrentUser(other, None)
    assert (await client.get(SHARES)).json() == []
    assert (await client.get(path)).status_code == 404
    mark = await client.patch(f"{path}/comments/{comment_id}", json={"reviewed": True})
    assert mark.status_code == 404
    assert (await client.delete(path)).status_code == 404
    assert (await client.post(SHARES, json=proposal)).status_code == 404
    act_as(app, app.state.local_user_id)
    app.dependency_overrides.pop(get_interface_user)


async def test_owner_confirms_snapshot_guest_comments_and_revocation_blocks_access(
    app: FastAPI, mentor_client: httpx.AsyncClient
) -> None:
    client = mentor_client
    packet_id, digest, proof_id = await seed_packet(app)
    proposal = {
        "packet_id": packet_id,
        "expected_digest": digest,
        "valid_hours": 24,
        "confirmed": True,
    }
    assert (await client.post(SHARES, json=proposal | {"confirmed": False})).status_code == 422
    assert (
        await client.post(SHARES, json=proposal | {"expected_digest": "0" * 64})
    ).status_code == 409
    created = await client.post(SHARES, json=proposal)
    assert created.status_code == 201, created.text
    assert created.headers["cache-control"] == "private, no-store"
    token = created.json()["token"]
    path = f"{SHARES}/{created.json()['share']['id']}"
    bearer = {"Authorization": f"Bearer {token}"}
    assert (await client.get(SHARED)).status_code == 404
    shared = await client.get(SHARED, headers=bearer)
    assert shared.status_code == 200 and shared.json()["digest"] == digest
    assert shared.json()["manifest"]["proofs"][0]["artifact"] == ARTIFACT
    assert token not in (await client.get(SHARES)).text

    body = {"proof_id": proof_id, "text": "Les deux mesures sont faciles à vérifier."}
    outside = body | {"proof_id": str(uuid4())}
    assert (
        await client.post(f"{SHARED}/comments", json=outside, headers=bearer)
    ).status_code == 422
    comment = await client.post(f"{SHARED}/comments", json=body, headers=bearer)
    assert comment.status_code == 201 and comment.json()["proof_id"] == proof_id

    await _assert_other_cannot_manage_share(app, client, proposal, path, comment.json()["id"])

    assert (await client.delete(path)).status_code == 204
    assert (await client.get(SHARED, headers=bearer)).status_code == 404
    assert (await client.post(f"{SHARED}/comments", json=body, headers=bearer)).status_code == 404
    retained = (await client.get(path)).json()
    assert retained["status"] == "revoked"
    assert retained["comments"] == [comment.json() | {"reviewed": False}]


async def test_expired_capability_cannot_read_or_comment(
    app: FastAPI, mentor_client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    packet_id, digest, proof_id = await seed_packet(app)
    issued = await mentor_client.post(
        SHARES,
        json={
            "packet_id": packet_id,
            "expected_digest": digest,
            "valid_hours": 1,
            "confirmed": True,
        },
    )
    assert issued.status_code == 201, issued.text
    moment = utcnow() + timedelta(hours=2)
    monkeypatch.setattr("app.features.mentor_reviews.service.utcnow", lambda: moment)
    headers = {"Authorization": f"Bearer {issued.json()['token']}"}
    assert (await mentor_client.get(SHARED, headers=headers)).status_code == 404
    payload = {"proof_id": proof_id, "text": "Tentative après expiration."}
    response = await mentor_client.post(f"{SHARED}/comments", json=payload, headers=headers)
    assert response.status_code == 404
    assert (await mentor_client.get(SHARES)).json()[0]["status"] == "expired"


async def test_mcp_can_mark_and_undo_a_comment_without_granting_access(
    app: FastAPI, mentor_client: httpx.AsyncClient
) -> None:
    client = mentor_client
    packet_id, digest, proof_id = await seed_packet(app)
    issued = (
        await client.post(
            SHARES,
            json={
                "packet_id": packet_id,
                "expected_digest": digest,
                "valid_hours": 24,
                "confirmed": True,
            },
        )
    ).json()
    share_id = issued["share"]["id"]
    guest = {"Authorization": f"Bearer {issued['token']}"}
    comment = await client.post(
        f"{SHARED}/comments",
        headers=guest,
        json={"proof_id": proof_id, "text": "Vérification faite."},
    )
    assert comment.status_code == 201 and "reviewed" not in comment.json()

    mcp = Mcp(client)
    writer = await mcp.token(("mentor_reviews",), "write")
    names = {
        tool["name"] for tool in (await mcp.rpc(writer, "tools/list")).json()["result"]["tools"]
    }
    assert "mentor_reviews_mark_comment" in names
    assert "mentor_reviews_issue_share" not in names and "mentor_reviews_revoke_share" not in names
    result, failed = await call(
        mcp,
        writer,
        "mentor_reviews_mark_comment",
        {
            "share_id": share_id,
            "comment_id": comment.json()["id"],
            "reviewed": True,
        },
    )
    assert not failed and result["data"]["reviewed"] is True
    path = f"{SHARES}/{share_id}"
    assert (await client.get(path)).json()["comments"][0]["reviewed"] is True
    changes = (await client.get("/api/v1/mcp/changes")).json()
    change = next(row for row in changes if row["action"] == "mentor_reviews_mark_comment")
    assert (await client.post(f"/api/v1/mcp/changes/{change['call_id']}/undo")).status_code == 200
    assert (await client.get(path)).json()["comments"][0]["reviewed"] is False
    assert (await client.get(SHARED, headers=guest)).status_code == 200
