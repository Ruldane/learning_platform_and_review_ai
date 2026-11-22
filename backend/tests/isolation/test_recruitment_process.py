"""Le parcours simulé reste privé et ne permet pas de sauter d’étape."""

from fastapi import FastAPI

from tests.features.postings.conftest import add_posting
from tests.isolation.conftest import Browser
from tests.support.gap import analysis_data

API = "/api/v1/recruitment-processes"


async def test_analyzed_offer_and_rehearsal_are_scoped_to_the_account(
    google_app: FastAPI, google_client_factory: Browser
) -> None:
    owner = await google_client_factory("rehearsal-a@example.test")
    other = await google_client_factory("rehearsal-b@example.test")
    user_id = (await owner.get("/api/v1/auth/me")).json()["id"]
    posting = await add_posting(
        google_app.state.session_factory,
        user_id,
        title="Ingénieure données",
        company="Société fictive",
        status="ready",
        analysis=analysis_data(),
    )
    options = await owner.get(f"{API}/options")
    assert options.status_code == 200
    assert [choice["id"] for choice in options.json()["postings"]] == [posting]
    assert (await other.get(f"{API}/options")).json()["postings"] == []
    body = {"posting_id": posting}
    created = await owner.post(API, json=body)
    assert created.status_code == 201, created.text
    row = created.json()
    assert row["active_step"] == "project" and row["missing_proofs"]
    assert [step["kind"] for step in row["steps"]] == ["project", "exercise", "interview"]
    assert (await other.post(API, json=body)).status_code == 404
    assert (await other.get(API)).json() == []
    path = f"{API}/{row['id']}"
    assert (await other.get(path)).status_code == 404
    answer = {"answer": "Je décris mon raisonnement."}
    assert (await other.post(f"{path}/steps/project/answers", json=answer)).status_code == 404
    assert (await owner.post(f"{path}/steps/exercise/answers", json=answer)).status_code == 409
