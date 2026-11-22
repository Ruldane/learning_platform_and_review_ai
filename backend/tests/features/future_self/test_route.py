"""Projection via HTTP a partir des relevés et du programme durable."""

import httpx
import pytest
from fastapi import FastAPI

from tests.features.future_self.support import API, freeze_clock, seed


async def test_projection_uses_role_offers_current_levels_and_remaining_work(
    client: httpx.AsyncClient, app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    freeze_clock(monkeypatch)
    refs = await seed(app, app.state.local_user_id)
    response = await client.get(
        API, params={"role": "ingenieur ia", "alternative_weekly_minutes": 240}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["role"], body["zone"], body["program_id"], body["as_of"]) == (
        "Ingénieur IA",
        "France",
        refs.program_id,
        "2026-11-16",
    )
    assert body["sample"]["run_id"] == refs.run_id and body["sample"]["analyzed"] == 4
    assert (body["offer_count"], body["current_percent"], body["observed_weeks"]) == (4, 25, 4)
    assert [
        (
            scenario["kind"],
            scenario["weekly_minutes"],
            scenario["target_date"],
            scenario["projected_percent"],
        )
        for scenario in body["scenarios"]
    ] == [
        ("observed", 120, "2026-11-23", 75),
        ("planned", 180, "2026-11-21", 75),
        ("alternative", 240, "2026-11-20", 75),
    ]
    [recommended] = body["recommendations"]
    assert recommended["chapter"] == {
        "program_id": refs.program_id,
        "module_id": refs.module_id,
        "lesson_id": refs.lesson_id,
        "title": "Recherche augmentée",
        "minutes": 120,
        "skills": ["Recherche augmentée"],
    }
    assert recommended["offers_unlocked"] == 2
    assert body["uncertainty"] == ["small_offer_sample"]


async def test_projection_query_validation_keeps_inputs_out_of_errors(
    client: httpx.AsyncClient,
    app: FastAPI,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    freeze_clock(monkeypatch)
    secret = "DONNEE-FICTIVE-DE-ROLE"
    response = await client.get(API, params={"role": secret * 25, "target_percent": 101})
    assert response.status_code == 422 and secret not in response.text
    assert set(response.json()["error"]["details"]["fields"]) == {"role", "target_percent"}
