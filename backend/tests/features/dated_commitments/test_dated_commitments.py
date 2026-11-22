from datetime import UTC, datetime
from uuid import uuid4

import httpx
from fastapi import FastAPI
from pytest import MonkeyPatch

from app.features.dated_commitments import service

API = "/api/v1/dated-commitments"


def commitment() -> dict[str, str]:
    return {
        "request_id": str(uuid4()),
        "title": "Changer la fréquence des révisions",
        "version": "v2",
        "intention": "Mesurer le temps nécessaire à une révision.",
        "indicator": "Durée médiane",
        "unit": "min",
        "target": "4.25",
        "due_on": "2030-01-08",
    }


async def test_observation_keeps_the_original_context_and_exact_gap(
    app: FastAPI, client: httpx.AsyncClient, monkeypatch: MonkeyPatch
) -> None:
    now = datetime(2030, 1, 7, 10, tzinfo=UTC)
    monkeypatch.setattr(service, "utcnow", lambda: now)
    action = commitment()
    created = await client.post(API, json=action)
    assert created.status_code == 201, created.text
    item = created.json()
    assert item["status"] == "scheduled"
    assert item["delta"] is None
    assert (await client.post(API, json=action)).json() == item
    assert (await client.post(API, json={**action, "target": "5"})).status_code == 409
    path = f"{API}/{item['id']}"
    assert (await client.post(f"{path}/review", json={"observed": "3.50"})).status_code == 409

    now = datetime(2030, 1, 8, 10, tzinfo=UTC)
    due = (await client.get(path)).json()
    assert due["status"] == "due" and due["delta"] is None
    reviewed = await client.post(
        f"{path}/review", json={"observed": "3.50", "note": "Après trois révisions."}
    )
    assert reviewed.status_code == 200, reviewed.text
    result = reviewed.json()
    assert result["status"] == "reviewed" and result["delta"] == "-0.75"
    assert result["version"] == action["version"] and result["intention"] == action["intention"]
    assert (await client.get(API)).json() == [result]
    replay = await client.post(
        f"{path}/review", json={"observed": "3.5", "note": "Après trois révisions."}
    )
    assert replay.json() == result
    conflicted = await client.post(f"{path}/review", json={"observed": "3.6"})
    assert conflicted.status_code == 409
