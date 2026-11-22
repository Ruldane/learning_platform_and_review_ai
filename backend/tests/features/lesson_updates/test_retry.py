import json

import httpx
from fastapi import FastAPI

from app.features.lesson_updates.service.schedule import scan_user
from tests.agents.graphs.lesson_support import LessonModels
from tests.features.lesson_updates.fixtures import BEFORE, CORRECTION, MARKER, seed_update
from tests.support.lesson_verification import wait_session
from tests.support.lessons import verifier_reply


async def test_failed_preparation_restarts_only_on_explicit_request(
    lesson_models: LessonModels, app: FastAPI, client: httpx.AsyncClient
) -> None:
    source = await seed_update(app)
    base = f"/api/v1/lessons/{source.lesson_id}"
    path = base + "/updates"
    invalid = json.dumps(
        {
            "explanation": "Le code ne contient encore aucun remplacement.",
            "replacements": [{"block": 1, "code": "print(12345)"}],
        }
    )
    lesson_models.when("verifier", MARKER, invalid, CORRECTION)
    owner = app.state.local_user_id
    assert await scan_user(app.state.lessons, owner) == 1
    [original] = (await client.get(path)).json()
    await wait_session(client, original["preparation_session_id"])
    assert (await client.get(path)).json()[0]["state"] == "failed"
    assert await scan_user(app.state.lessons, owner) == 0
    retry = await client.post(f"{path}/{original['id']}/accept")
    assert retry.status_code == 202, retry.text
    assert retry.json()["session_id"] != original["preparation_session_id"]
    await wait_session(client, retry.json()["session_id"])
    assert (await client.get(path)).json()[0]["state"] == "ready"
    assert BEFORE in (await client.get(base)).json()["markdown"]


async def test_failed_publication_can_be_retried(
    lesson_models: LessonModels, app: FastAPI, client: httpx.AsyncClient
) -> None:
    source = await seed_update(app)
    path = f"/api/v1/lessons/{source.lesson_id}/updates"
    lesson_models.when("verifier", MARKER, CORRECTION)
    lesson_models.when(
        "verifier", "", verifier_reply("Une affirmation non étayée."), verifier_reply()
    )
    assert await scan_user(app.state.lessons, app.state.local_user_id) == 1
    [original] = (await client.get(path)).json()
    await wait_session(client, original["preparation_session_id"])
    endpoint = f"{path}/{original['id']}/accept"
    initial = (await client.post(endpoint)).json()["session_id"]
    await wait_session(client, initial)
    assert (await client.get(path)).json()[0]["state"] == "failed"
    retry = (await client.post(endpoint)).json()["session_id"]
    assert retry != initial
    await wait_session(client, retry)
    assert (await client.get(path)).json()[0]["state"] == "published"
