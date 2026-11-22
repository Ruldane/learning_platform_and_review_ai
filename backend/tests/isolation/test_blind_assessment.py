"""Les deux sources et l’épreuve restent privées, le résultat n’est pas anticipé."""

from fastapi import FastAPI

from tests.features.blind_assessment.support import seed_versions
from tests.isolation.conftest import Browser

API = "/api/v1/blind-assessments"


async def test_version_identity_is_withheld_and_other_accounts_cannot_access(
    google_app: FastAPI, google_client_factory: Browser
) -> None:
    owner = await google_client_factory("blind-owner@example.test")
    other = await google_client_factory("blind-other@example.test")
    user_id = (await owner.get("/api/v1/auth/me")).json()["id"]
    first, second = await seed_versions(google_app, user_id)
    body = {"first_version_id": first, "second_version_id": second, "rubric": "clarity"}
    options = await owner.get(f"{API}/options")
    assert options.status_code == 200
    assert {item["id"] for item in options.json()["sources"]} == {first, second}
    assert (await other.get(f"{API}/options")).json()["sources"] == []
    created = await owner.post(API, json=body)
    assert created.status_code == 201, created.text
    assert first not in created.text and second not in created.text
    assert created.json()["result"] is None
    assert (await other.post(API, json=body)).status_code == 404
    path = f"{API}/{created.json()['id']}"
    assert (await other.get(path)).status_code == 404
    assert (await other.post(f"{path}/evaluate")).status_code == 404
    assert (await other.get(API)).json() == []
