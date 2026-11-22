import httpx
from fastapi import FastAPI

from app.db.models.accounts import User
from tests.features.interprogram_planning.support import MONDAY, dates, seed_week
from tests.sessions_support import act_as

API = "/api/v1/interprogram-planning"


async def test_selected_programs_and_plans_are_scoped(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    programs, tasks = await seed_week(app)
    action = {"week_start": MONDAY.isoformat(), "program_ids": programs}
    proposed = await client.post(API, json=action)
    assert proposed.status_code == 201, proposed.text
    other = "other-planning-account"
    async with app.state.session_factory() as db:
        db.add(User(id=other, user_id=other))
        await db.commit()
    act_as(app, other)
    assert (await client.get(f"{API}/options")).json() == []
    assert (await client.get(API)).json() == []
    assert (await client.post(API, json=action)).status_code == 404
    path = f"{API}/{proposed.json()['id']}/accept"
    assert (await client.post(path, json={"confirmed": True})).status_code == 404
    assert await dates(app, tasks) == [MONDAY] * 3
