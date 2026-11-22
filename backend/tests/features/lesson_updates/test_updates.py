"""Une version annoncée déclenche une seule correction, approuvée avant publication."""

import httpx
from fastapi import FastAPI

from tests.agents.graphs.lesson_support import LessonModels
from tests.features.lesson_updates.fixtures import (
    AFTER,
    BEFORE,
    CORRECTION,
    MARKER,
    RELEASE,
    seed_update,
)
from tests.support.lesson_verification import wait_session
from tests.support.lessons import verifier_reply


async def test_update_is_grounded_deduplicated_and_published_only_after_acceptance(
    lesson_models: LessonModels, app: FastAPI, client: httpx.AsyncClient
) -> None:
    source = await seed_update(app)
    root = f"/api/v1/lessons/{source.lesson_id}"
    path = root + "/updates"
    empty = await client.get(path)
    assert empty.status_code == 200 and empty.json() == [], empty.text

    from app.features.lesson_updates.service.schedule import scan_user

    lesson_models.when("verifier", MARKER, CORRECTION)
    lesson_models.when("verifier", "", verifier_reply(), verifier_reply())
    owner: str = app.state.local_user_id
    assert await scan_user(app.state.lessons, owner) == 1
    assert await scan_user(app.state.lessons, owner) == 0
    (queued,) = (await client.get(path)).json()
    assert queued["apis"] == ["fictilib.old_api"]
    assert queued["source_url"] == RELEASE and queued["version"] == "2.0.0"
    finished = await wait_session(client, queued["preparation_session_id"])
    assert finished["status"] == "completed", finished
    (proposal,) = (await client.get(path)).json()
    assert proposal["state"] == "ready"
    assert proposal["changes"][0]["before"] == BEFORE
    assert proposal["changes"][0]["after"] == AFTER
    assert BEFORE in (await client.get(root)).json()["markdown"]

    accepted = await client.post(f"{path}/{proposal['id']}/accept")
    assert accepted.status_code == 202, accepted.text
    verified = await wait_session(client, accepted.json()["session_id"])
    assert verified["status"] == "completed", verified
    published = (await client.get(root)).json()["markdown"]
    assert AFTER in published and BEFORE not in published
    assert "fictilib.unused_api" in published
    assert (await client.get(path)).json()[0]["state"] == "published"
