from uuid import uuid4

import httpx
from fastapi import FastAPI

from tests.features.lessons.test_router import seed
from tests.sessions_support import act_as


async def test_classroom_cannot_open_another_accounts_lesson(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    lesson = await seed(app)
    path = f"/api/v1/lessons/{lesson.lesson_id}/classroom"
    act_as(app, "autre-utilisatrice")
    message = {"request_id": str(uuid4()), "question": "Une explication fictive."}
    for refused in (await client.get(path), await client.post(path + "/messages", json=message)):
        assert refused.status_code == 404
        assert refused.json()["error"]["code"] == "lesson_not_found"
        assert message["question"] not in refused.text
