"""Recette API du consentement Agenda, sur le port factice."""

from datetime import UTC, datetime
from urllib.parse import parse_qs, urlsplit

import httpx
from fastapi import FastAPI

from app.core.deps import get_current_user, get_interface_user
from app.providers.calendar.fake import FakeCalendar
from tests.features.calendar.support import seed_program
from tests.sessions_support import act_as

PATH = "/api/v1/calendar"
NOW = datetime(2026, 11, 16, 7, tzinfo=UTC)


async def test_connection_requires_consent_and_selected_event_is_replayed_once(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    assert (await client.get(f"{PATH}/connection")).json()["status"] == "unconfigured"
    provider = FakeCalendar()
    app.state.calendar.port = provider
    app.state.calendar.now = lambda: NOW
    assert (await client.post(f"{PATH}/connection", json={"consent": False})).status_code == 422
    assert provider.exchanges == 0

    state = await connect(client)
    duplicate = await client.get(f"{PATH}/callback", params={"state": state, "code": "fake"})
    assert "agenda=error" in duplicate.headers["location"]
    assert provider.exchanges == 1

    program, task = await seed_program(app)
    body = {"kind": "study", "program_id": program, "source_id": task}
    preview = await client.post(f"{PATH}/proposals", json=body)
    assert preview.status_code == 201, preview.text
    assert provider.events == {}
    proposed = preview.json()
    assert proposed["start"].startswith("2026-11-16T08:00:00")
    operation = f"{PATH}/proposals/{proposed['id']}/confirm"
    assert (await client.post(operation)).json()["status"] == "synced"
    assert (await client.post(operation)).json()["status"] == "synced"
    assert len(provider.events) == provider.writes == 1

    act_as(app, "autre-compte")
    app.dependency_overrides[get_interface_user] = app.dependency_overrides[get_current_user]
    assert (await client.post(operation)).status_code == 404
    assert (await client.get(f"{PATH}/connection")).json()["status"] == "disconnected"
    assert provider.writes == 1


async def connect(client: httpx.AsyncClient) -> str:
    started = await client.post(f"{PATH}/connection", json={"consent": True})
    assert started.status_code == 200, started.text
    url = urlsplit(started.json()["authorization_url"])
    state = parse_qs(url.query)["state"][0]
    returned = await client.get(f"{PATH}/callback", params={"state": state, "code": "fake"})
    assert returned.status_code == 303
    assert "agenda=connected" in returned.headers["location"]
    assert (await client.get(f"{PATH}/connection")).json()["status"] == "connected"
    return state
