from uuid import uuid4

import httpx
from fastapi import FastAPI

from app.db.models.accounts import User
from tests.sessions_support import act_as


async def test_private_replay_cannot_be_read_or_annotated(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    outsider = "autre-compte-replay"
    async with app.state.session_factory() as db:
        db.add(User(id=outsider, user_id=outsider))
        await db.commit()
    endpoint = "/api/v1/incident-replays"
    response = await client.post(endpoint, json={"scenario": "orders-v1", "receipt": str(uuid4())})
    assert response.status_code == 201, response.text
    path = f"{endpoint}/{response.json()['id']}"
    act_as(app, outsider)
    assert (await client.get(endpoint)).json() == []
    assert (await client.get(path)).status_code == 404
    note = {"step": 1, "hypothesis": "Note étrangère"}
    assert (await client.post(f"{path}/notes", json=note)).status_code == 404
