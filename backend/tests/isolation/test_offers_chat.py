from uuid import uuid4

import httpx
from fastapi import FastAPI

from tests.sessions_support import act_as

OFFERS = "/api/v1/conversations/offers"


async def test_offers_chats_are_separate_and_private(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    first = await client.post(OFFERS)
    assert first.status_code == 201, first.text
    second = await client.post(OFFERS)
    assert second.status_code == 201, second.text
    first_id, second_id = first.json()["id"], second.json()["id"]
    assert first_id != second_id
    assert (await client.get(f"{OFFERS}/{first_id}")).json()["turns"] == []
    assert (await client.get(f"{OFFERS}/{second_id}")).json()["turns"] == []
    assert {thread["id"] for thread in (await client.get(OFFERS)).json()} == {first_id, second_id}

    brain = await client.post("/api/v1/brain/conversations")
    assert brain.status_code == 201, brain.text
    assert (await client.get(f"{OFFERS}/{brain.json()['id']}")).status_code == 404
    assert (
        await client.get("/api/v1/brain/conversation", params={"conversation_id": first_id})
    ).status_code == 404

    act_as(app, "another-offers-account")
    assert (await client.get(OFFERS)).json() == []
    path = f"{OFFERS}/{first_id}"
    assert (await client.get(path)).status_code == 404
    body = {"request_id": str(uuid4()), "question": "Who should I contact?"}
    assert (await client.post(f"{path}/messages", json=body)).status_code == 404
    assert (await client.patch(path, json={"title": "Other user's chat"})).status_code == 404
    assert (await client.delete(path)).status_code == 404
