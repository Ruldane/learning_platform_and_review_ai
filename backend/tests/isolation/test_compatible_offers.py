import httpx
from fastapi import FastAPI

from app.db.models.accounts import User
from tests.e2e.compatible_offers import SKILL, TITLE, seed_alert
from tests.sessions_support import act_as


async def test_alert_and_plan_exclude_other_accounts(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    owner = app.state.local_user_id
    run = await seed_alert(app, owner)
    path = f"/api/v1/compatible-offers/{run}/p1"
    visible = await client.get(path)
    assert visible.status_code == 200, visible.text
    result = visible.json()
    assert result["title"] == TITLE and result["rows"][0]["skill"] == SKILL
    assert result["rows"][0]["action"] == "to_add"
    invalid = await client.post(path + "/plan", json={"skills": ["Autre compétence"]})
    assert invalid.status_code == 422
    other = "autre-compte-alerte"
    async with app.state.session_factory() as db:
        db.add(User(id=other, user_id=other))
        await db.commit()
    act_as(app, other)
    assert (await client.get(path)).status_code == 404
    assert (await client.post(path + "/plan", json={"skills": [SKILL]})).status_code == 404
