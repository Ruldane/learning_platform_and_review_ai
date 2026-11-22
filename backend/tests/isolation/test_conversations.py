from uuid import uuid4

import httpx
from fastapi import FastAPI

from app.core.deps import CurrentUser, get_interface_user
from tests.features.ide.support import new_session
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


async def test_feynman_context_and_report_are_private(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    lesson = await seed(app)
    project = await new_session(client, {"main.py": "private_example = 42"})
    lesson_path = f"/api/v1/lessons/{lesson.lesson_id}/explain"
    ide_path = f"/api/v1/ide/sessions/{project['id']}/explain"
    lesson_body = {"request_id": str(uuid4())}
    ide_body = {"request_id": str(uuid4()), "path": "main.py"}
    assert (await client.post(lesson_path, json=lesson_body)).status_code == 202
    assert (await client.post(ide_path, json=ide_body)).status_code == 202
    turn = (await client.get(ide_path)).json()
    report_path = f"/api/v1/conversations/explain/{turn['id']}"
    app.dependency_overrides[get_interface_user] = lambda: CurrentUser(id="autre", email=None)
    responses = [
        await client.get(lesson_path),
        await client.post(lesson_path, json=lesson_body),
        await client.get(ide_path),
        await client.post(ide_path, json=ide_body),
        await client.get(report_path),
        await client.post(report_path + "/accept"),
    ]
    assert all(response.status_code == 404 for response in responses)
    assert all("private_example" not in response.text for response in responses)
