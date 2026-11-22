import httpx
from fastapi import FastAPI

from app.db.models.accounts import User
from tests.features.dated_commitments.test_dated_commitments import API, commitment
from tests.sessions_support import act_as


async def test_decisions_and_reviews_are_private(app: FastAPI, client: httpx.AsyncClient) -> None:
    created = await client.post(API, json=commitment())
    assert created.status_code == 201, created.text
    path = f"{API}/{created.json()['id']}"
    other = "other-commitment-account"
    async with app.state.session_factory() as db:
        db.add(User(id=other, user_id=other))
        await db.commit()
    act_as(app, other)
    assert (await client.get(API)).json() == []
    assert (await client.get(path)).status_code == 404
    assert (await client.post(f"{path}/review", json={"observed": "4.25"})).status_code == 404
