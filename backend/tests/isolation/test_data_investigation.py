import httpx
from fastapi import FastAPI

from app.db.models.accounts import User
from tests.sessions_support import act_as


async def test_investigation_owner_only(app: FastAPI, client: httpx.AsyncClient) -> None:
    owner = "autre-compte-enquete"
    async with app.state.session_factory() as db:
        db.add(User(id=owner, user_id=owner))
        await db.commit()
    endpoint = "/api/v1/data-investigations"
    created = await client.post(endpoint, json={"dataset": "supplies-v1"})
    assert created.status_code == 201, created.text
    path = f"{endpoint}/{created.json()['id']}"
    act_as(app, owner)
    assert (await client.get(endpoint)).json() == []
    assert (await client.get(path)).status_code == 404
    assert (await client.patch(path, json={"operations": ["delivered_only"]})).status_code == 404
    assert (
        await client.post(f"{path}/submit", json={"deliveries": 3, "units": 20})
    ).status_code == 404
