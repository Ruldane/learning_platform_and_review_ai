import httpx
from fastapi import FastAPI

from app.db.models.accounts import User
from tests.sessions_support import act_as


async def test_meeting_module_is_private(app: FastAPI, client: httpx.AsyncClient) -> None:
    other = "autre-compte-reunion"
    async with app.state.session_factory() as db:
        db.add(User(id=other, user_id=other))
        await db.commit()
    endpoint = "/api/v1/meeting-modules"
    created = await client.post(
        endpoint,
        json={"title": "Module privé", "transcript": "Décision : Comparer pendant une semaine."},
    )
    assert created.status_code == 201, created.text
    path = f"{endpoint}/{created.json()['id']}"
    act_as(app, other)
    assert (await client.get(endpoint)).json() == []
    assert (await client.get(path)).status_code == 404
    selection = {"lines": [1]}
    assert (await client.put(f"{path}/selection", json=selection)).status_code == 404
    assert (await client.post(f"{path}/publish", json=selection)).status_code == 404
