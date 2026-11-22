import httpx
from fastapi import FastAPI

from app.db.models.accounts import User
from tests.features.missions.support import seed_posting
from tests.sessions_support import act_as

API = "/api/v1/missions"


async def test_mission_and_posting_are_scoped_to_the_account(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    owner = app.state.local_user_id
    posting = await seed_posting(app)
    response = await client.post(API, json={"posting_id": posting, "requirement_indices": [0]})
    assert response.status_code == 201
    path = f"{API}/{response.json()['id']}"
    other = "autre-compte-missions"
    async with app.state.session_factory() as db:
        db.add(User(id=other, user_id=other))
        await db.commit()
    act_as(app, other)
    assert (await client.get(API)).json() == []
    assert (await client.get(path)).status_code == 404
    assert (
        await client.patch(f"{path}/criteria/0", json={"revision": 0, "observed": 2})
    ).status_code == 404
    assert (
        await client.post(f"{path}/submission", json={"revision": 0, "artifact": "Privé"})
    ).status_code == 404
    assert (
        await client.post(API, json={"posting_id": posting, "requirement_indices": [0]})
    ).status_code == 404
    act_as(app, owner)
    assert (await client.get(path)).json()["revision"] == 0
