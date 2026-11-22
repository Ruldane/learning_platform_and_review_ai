import asyncio
from uuid import uuid4

import httpx

from tests.features.quiz.conftest import Seeded
from tests.features.quiz.test_cards import API, TODAY, _cards


async def test_offline_receipt_replays_once_for_its_original_card_due_date(
    client: httpx.AsyncClient, seeded: Seeded
) -> None:
    [card_id] = await _cards(seeded, 1)
    path = f"{API}/flashcards/{card_id}/review"
    body = {"result": "ok", "receipt": {"id": str(uuid4()), "due_date": TODAY.isoformat()}}
    first, duplicate = await asyncio.gather(
        client.post(path, json=body), client.post(path, json=body)
    )
    assert first.status_code == duplicate.status_code == 200
    assert first.json() == duplicate.json() and first.json()["step"] == 3
    conflict = await client.post(path, json={**body, "result": "fail"})
    assert (
        conflict.status_code == 409 and conflict.json()["error"]["code"] == "card_receipt_changed"
    )
    late = await client.post(
        path, json={**body, "receipt": {**body["receipt"], "id": str(uuid4())}}
    )
    assert late.status_code == 409 and late.json()["error"]["code"] == "card_not_due"
