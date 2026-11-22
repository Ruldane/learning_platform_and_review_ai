from uuid import uuid4

import httpx
from fastapi import FastAPI

from tests.sessions_support import act_as, wait_status

CHAT = "/api/v1/brain/conversation"


async def test_brain_thread_is_private_to_each_account(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    body = {"request_id": str(uuid4()), "question": "Une question privée."}
    headers = {"X-Tremplin-Run": "codex"}
    first = await client.post(f"{CHAT}/messages", json=body, headers=headers)
    assert first.status_code == 202
    sid = first.json()["session_id"]
    await wait_status(client, sid, "waiting_user")
    own = (await client.get(CHAT)).json()
    assert own["turns"][0]["question"] == body["question"]

    act_as(app, "un-autre-compte")
    assert (await client.get(CHAT)).json() is None
    second = await client.post(
        f"{CHAT}/messages", json=body | {"question": "Autre sujet."}, headers=headers
    )
    assert second.status_code == 202 and second.json()["session_id"] != sid
    other = (await client.get(CHAT)).json()
    assert own["id"] != other["id"]
    assert [turn["question"] for turn in other["turns"]] == ["Autre sujet."]
