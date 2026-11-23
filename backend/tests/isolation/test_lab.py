from dataclasses import replace

import httpx
from fastapi import FastAPI

from tests.isolation.conftest import Browser

PREFERENCES = "/api/v1/lab/preferences"


async def test_lab_preferences_belong_to_one_account(google_client_factory: Browser) -> None:
    owner = await google_client_factory("january@example.com")
    other = await google_client_factory("autre@example.com")
    assert (await owner.get(PREFERENCES)).json() == {"pinned": [], "tour": "pending"}
    update = await owner.patch(PREFERENCES, json={"pinned": ["oncall"], "tour": "disabled"})
    assert update.json() == {"pinned": ["oncall"], "tour": "disabled"}
    assert (await other.get(PREFERENCES)).json() == {"pinned": [], "tour": "pending"}
    assert (await owner.patch(PREFERENCES, json={"pinned": ["settings"]})).status_code == 422
    assert (await owner.patch(PREFERENCES, json={"tour": "done"})).json() == {
        "pinned": ["oncall"],
        "tour": "done",
    }


async def test_podcast_reports_the_audio_key_independently(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    existing = app.state.providers
    keys = {"anthropic": "fixture-anthropic"}
    try:
        app.state.providers = replace(existing, env_keys=keys)
        settings = (await client.get("/api/v1/settings")).json()
        for tier in settings["tiers"].values():
            tier["provider"] = "anthropic"
            tier["model"] = "claude-sonnet-4-6"
        changed = await client.put("/api/v1/settings", json=settings)
        assert changed.status_code == 200, changed.text
        assert await _podcast_requirements(client) == ["openai_audio"]
        app.state.providers = replace(existing, env_keys={**keys, "openai": "fixture-openai"})
        assert await _podcast_requirements(client) == []
    finally:
        app.state.providers = existing


async def _podcast_requirements(client: httpx.AsyncClient) -> list[str]:
    listing = await client.get("/api/v1/lab/overview")
    assert listing.status_code == 200, listing.text
    return next(
        feature["missing_prerequisites"]
        for section in listing.json()["sections"]
        for feature in section["features"]
        if feature["id"] == "podcast"
    )
