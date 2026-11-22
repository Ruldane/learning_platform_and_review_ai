from uuid import uuid4

import httpx

API = "/api/v1/incident-replays"


async def test_replay_stores_an_annotation_at_the_selected_timestamp(
    client: httpx.AsyncClient,
) -> None:
    catalog = await client.get(f"{API}/scenarios")
    assert catalog.status_code == 200, catalog.text
    assert len(catalog.json()) >= 2
    body = {"scenario": "orders-v1", "receipt": str(uuid4())}
    created = await client.post(API, json=body)
    assert created.status_code == 201, created.text
    replay = created.json()
    assert (await client.post(API, json=body)).json() == replay
    assert len(replay["timeline"]) >= 3
    assert replay["timeline"][0]["minute"] == 0
    path = f"{API}/{replay['id']}"
    note = {"step": 1, "hypothesis": "Consulter le taux de reprise à la minute 4."}
    saved = await client.post(f"{path}/notes", json=note)
    assert saved.status_code == 200, saved.text
    assert saved.json()["notes"] == [note]
    assert (await client.post(f"{path}/notes", json=note)).json() == saved.json()
    invalid = {**note, "step": 90}
    assert (await client.post(f"{path}/notes", json=invalid)).status_code == 422
    restored = (await client.get(path)).json()
    assert restored["timeline"] == replay["timeline"]
    assert restored["notes"][0]["step"] == 1
