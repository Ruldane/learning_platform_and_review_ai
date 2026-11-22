from uuid import uuid4

import httpx
from fastapi import FastAPI

from tests.features.lessons.test_router import seed
from tests.sessions_support import act_as, wait_status


async def test_cannot_read_or_add_to_another_accounts_conversation(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    lesson = await seed(app)
    path = f"/api/v1/lessons/{lesson.lesson_id}/conversation"
    payload = {"request_id": str(uuid4()), "question": "Message privé."}
    started = await client.post(
        f"{path}/messages", json=payload, headers={"X-Tremplin-Run": "codex"}
    )
    assert started.status_code == 202
    await wait_status(client, started.json()["session_id"], "waiting_user")
    act_as(app, "un-autre-utilisateur")
    for refused in (await client.get(path), await client.post(f"{path}/messages", json=payload)):
        assert refused.status_code == 404
        assert refused.json()["error"]["code"] == "lesson_not_found"
        assert payload["question"] not in refused.text
