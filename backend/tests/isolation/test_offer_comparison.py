"""Deux offres privées, des critères du compte et un scénario figé."""

from fastapi import FastAPI

from app.db.models.postings import JobPosting
from tests.features.offer_comparison.support import seed_offers
from tests.isolation.conftest import Browser

API = "/api/v1/offer-comparisons"
PREFERENCES = {
    "weights": {"match": 40, "work_mode": 50, "location": 50},
    "preferred_work_mode": "hybrid",
    "preferred_location": "Lyon",
}


async def test_weights_missing_facts_sensitivity_and_frozen_history_are_private(
    google_app: FastAPI, google_client_factory: Browser
) -> None:
    owner = await google_client_factory("comparison-a@example.test")
    other = await google_client_factory("comparison-b@example.test")
    user_id = (await owner.get("/api/v1/auth/me")).json()["id"]
    first, second = await seed_offers(google_app, user_id)
    options = await owner.get(f"{API}/postings")
    assert options.status_code == 200
    assert {row["id"] for row in options.json()} == {first, second}
    assert (await other.get(f"{API}/postings")).json() == []
    assert (await owner.put(f"{API}/preferences", json=PREFERENCES)).json() == PREFERENCES
    assert (await other.get(f"{API}/preferences")).json() != PREFERENCES

    inputs = {"first_id": first, "second_id": second}
    assert (await other.post(f"{API}/preview", json=inputs)).status_code == 404
    assert (await other.post(API, json=inputs)).status_code == 404
    preview = await owner.post(f"{API}/preview", json=inputs)
    assert preview.status_code == 200, preview.text
    result = preview.json()
    assert result["preferences"] == PREFERENCES
    assert result["first"]["missing"] == result["second"]["missing"] == ["match"]
    assert result["first_score"] == result["second_score"] == 50
    assert result["leader"] == "tie"
    assert result["sensitivity"][1]["criterion"] == "work_mode"
    assert result["sensitivity"][1]["lower_leader"] == "second"
    assert result["sensitivity"][1]["higher_leader"] == "first"
    created = await owner.post(API, json=inputs)
    assert created.status_code == 201, created.text
    saved = created.json()
    assert saved["result"] == result
    path = f"{API}/{saved['id']}"
    assert (await other.get(path)).status_code == 404
    assert (await other.get(API)).json() == []
    await owner.put(f"{API}/preferences", json={**PREFERENCES, "preferred_location": None})
    async with google_app.state.session_factory() as db:
        row = await db.get(JobPosting, first)
        assert row is not None
        row.title = "Intitulé retouché"
        await db.commit()
    assert (await owner.get(path)).json() == saved
    assert (await owner.get(API)).json()[0]["id"] == saved["id"]
