import httpx
from fastapi import FastAPI

from app.db.models.accounts import User
from tests.features.error_atlas.support import HYPOTHESIS, seed_evidence
from tests.sessions_support import act_as

API = "/api/v1/error-atlas"


async def test_evidence_observations_and_exercises_belong_to_the_account(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    await seed_evidence(app)
    candidate = (await client.get(f"{API}/evidence")).json()[0]
    body = {"reference": candidate["reference"], "hypothesis": HYPOTHESIS, "confidence": "low"}
    saved = await client.post(f"{API}/observations", json=body)
    assert saved.status_code == 201
    path = f"{API}/hypotheses/{saved.json()['id']}/exercise"
    assert (await client.post(path)).status_code == 201

    other = "other-atlas-account"
    async with app.state.session_factory() as db:
        db.add(User(id=other, user_id=other))
        await db.commit()
    act_as(app, other)
    assert (await client.get(API)).json() == []
    assert (await client.get(f"{API}/evidence")).json() == []
    assert (await client.post(f"{API}/observations", json=body)).status_code == 404
    assert (await client.post(path)).status_code == 404
