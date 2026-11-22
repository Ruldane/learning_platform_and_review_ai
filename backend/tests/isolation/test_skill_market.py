"""Même la simulation des offres ne mélange pas deux comptes."""

import httpx
from fastapi import FastAPI

from app.db.models.accounts import User
from tests.e2e.skill_market import seed_market
from tests.features.future_self.support import ROLE, ZONE
from tests.sessions_support import act_as

API = "/api/v1/skill-market"


async def test_comparable_samples_and_hour_are_private(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    owner = app.state.local_user_id
    await seed_market(app, owner)
    params = {"role": ROLE, "zone": ZONE, "skill": "Recherche augmentée"}
    response = await client.get(API, params=params)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["current"]["analyzed"] == result["previous"]["analyzed"] == 4
    assert result["indicative"] is True
    row = next(item for item in result["quotes"] if item["name"] == "RAG")
    assert row["demand_percent"] == 50.0 and row["change_points"] == 25.0
    assert row["opportunity"] is True
    hour = result["simulation"]
    assert hour["remaining_minutes"] == 120 and hour["progress_percent"] == 50
    assert hour["covered_before"] == hour["covered_after"] == 1

    other = "autre-compte-bourse"
    async with app.state.session_factory() as db:
        db.add(User(id=other, user_id=other))
        await db.commit()
    act_as(app, other)
    protected = (await client.get(API, params=params)).json()
    assert protected["quotes"] == [] and protected["simulation"] is None
