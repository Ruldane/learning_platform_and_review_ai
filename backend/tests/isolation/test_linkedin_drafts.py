from fastapi import FastAPI

from app.db.models.linkedin_drafts import LinkedInDraft
from tests.e2e.linkedin_drafts import EDIT, SCRIPT, seed_profile
from tests.isolation.conftest import Browser

API = "/api/v1/linkedin-drafts"


async def test_draft_is_private_and_edits_are_checked(
    google_app: FastAPI, google_client_factory: Browser
) -> None:
    client = await google_client_factory("profil-maitre@example.test")
    other = await google_client_factory("autre-profil@example.test")
    owner = (await client.get("/api/v1/auth/me")).json()["id"]
    await seed_profile(google_app, owner)
    async with google_app.state.session_factory() as db:
        row = LinkedInDraft(
            user_id=owner, profile_version=1, session_id="session-test", revision=1, text=SCRIPT
        )
        db.add(row)
        await db.commit()
    draft = (await client.get(f"{API}/latest")).json()
    assert draft["claims"] == [{"field": "about", "term": "900"}]
    path = f"{API}/{row.id}"
    result = await client.put(path, json={"revision": 1, "text": EDIT})
    assert result.status_code == 200 and result.json()["claims"] == []
    assert (await client.put(path, json={"revision": 1, "text": EDIT})).status_code == 409
    assert (await other.get(f"{API}/latest")).json() is None
    assert (await other.put(path, json={"revision": 2, "text": EDIT})).status_code == 404
