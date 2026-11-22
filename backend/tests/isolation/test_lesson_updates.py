from fastapi import FastAPI

from app.db.base import new_id
from app.db.models.lesson_updates import LessonUpdate
from tests.features.lesson_updates.fixtures import RELEASE, TITLE, VERSION, seed_update
from tests.isolation.conftest import Browser


async def test_lesson_update_routes_are_isolated(
    google_app: FastAPI, google_client_factory: Browser
) -> None:
    owner = await google_client_factory("veille-propriete@example.test")
    other = await google_client_factory("veille-autre@example.test")
    user = (await owner.get("/api/v1/auth/me")).json()["id"]
    google_app.state.local_user_id = user
    seeded = await seed_update(google_app)
    update_id = new_id()
    async with google_app.state.session_factory() as db:
        db.add(
            LessonUpdate(
                id=update_id,
                user_id=user,
                lesson_id=seeded.lesson_id,
                library="fictilib",
                version=VERSION,
                source_url=RELEASE,
                base_hash="0" * 64,
                detected=[],
                preparation_session_id=new_id(),
                draft={"explanation": TITLE, "markdown": "brouillon fictif", "changes": []},
            )
        )
        await db.commit()
    path = f"/api/v1/lessons/{seeded.lesson_id}/updates"
    assert len((await owner.get(path)).json()) == 1
    stale = await owner.post(f"{path}/{update_id}/accept")
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "lesson_update_stale"
    for refused in (await other.get(path), await other.post(f"{path}/{update_id}/accept")):
        assert refused.status_code == 404
        assert RELEASE not in refused.text
