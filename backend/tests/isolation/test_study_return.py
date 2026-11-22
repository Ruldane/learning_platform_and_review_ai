from datetime import date

import httpx
from fastapi import FastAPI

from app.db.models.accounts import User
from tests.features.study_return.support import ACQUIRED, seed_return
from tests.sessions_support import act_as

API = "/api/v1/study-return"


async def test_return_plan_and_reminder_are_private(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    await seed_return(app)
    assert (await client.post(f"{API}/prepare")).status_code == 200
    assert (
        await client.put(f"{API}/reminder", json={"day": date.today().isoformat()})
    ).status_code == 200
    other = "other-study-return-account"
    async with app.state.session_factory() as db:
        db.add(User(id=other, user_id=other))
        await db.commit()

    act_as(app, other)
    assert (await client.get(API)).json() == {
        "plan": None,
        "reminder_on": None,
        "reminder_due": False,
    }
    assert (await client.post(f"{API}/start")).status_code == 409
    response = await client.post(f"{API}/prepare")
    assert response.status_code == 200 and ACQUIRED not in response.text
    plan = response.json()["plan"]
    assert plan["skills"] == [] and plan["cards"] == [] and plan["last_block"] is None
