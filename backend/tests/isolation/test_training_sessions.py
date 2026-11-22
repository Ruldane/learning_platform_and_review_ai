from uuid import uuid4

import httpx
from fastapi import FastAPI

from tests.features.study.test_training import TRAINING
from tests.sessions_support import act_as


async def test_training_routes_hide_another_accounts_session(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    opened = await client.post(TRAINING, json={})
    assert opened.status_code == 202
    path = f"{TRAINING}/{opened.json()['id']}"
    act_as(app, "un-autre-compte")
    assert (await client.get(f"{TRAINING}/open")).json() is None
    for refused in (
        await client.get(path),
        await client.patch(path, json={"action": "mode", "mode": "direct"}),
        await client.post(
            f"{path}/messages", json={"request_id": str(uuid4()), "question": "Pourquoi ?"}
        ),
    ):
        assert refused.status_code == 404
        assert refused.json()["error"]["code"] == "study_session_not_found"
    own = await client.post(TRAINING, json={})
    assert own.is_success and own.json()["id"] != opened.json()["id"]
