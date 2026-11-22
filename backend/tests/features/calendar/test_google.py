import json
from dataclasses import replace
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from app.core.errors import AppError
from app.providers.calendar.base import CalendarEvent, Interval
from app.providers.calendar.google import SCOPES, GoogleCalendar
from tests.features.calendar.test_flow import NOW

CALLBACK = "http://localhost:8000/api/v1/calendar/callback"


async def test_google_requests_minimal_scope_and_only_owned_event_paths() -> None:
    requests: list[httpx.Request] = []
    stored = {}

    def transport(req: httpx.Request) -> httpx.Response:
        requests.append(req)
        path = req.url.path
        if path == "/token":
            data = parse_qs(req.content.decode())
            if data["grant_type"] == ["authorization_code"]:
                assert data["redirect_uri"] == [CALLBACK]
                assert data["code_verifier"] == ["recette"]
                return httpx.Response(
                    200, json={"scope": " ".join(SCOPES), "refresh_token": "test"}
                )
            assert data["refresh_token"] == ["test"]
            return httpx.Response(200, json={"access_token": "access"})
        if path == "/calendar/v3/freeBusy":
            assert b'"id":"primary"' in req.content
            return httpx.Response(200, json={"calendars": {"key": {"busy": []}}})
        if req.method == "POST":
            assert path == "/calendar/v3/calendars/primary/events"
            assert req.url.params["sendUpdates"] == "none"
            assert b"attendees" not in req.content
            stored.update(json.loads(req.content))
            assert stored["visibility"] == "private"
            return httpx.Response(201, json={})
        return httpx.Response(200, json=stored) if stored else httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as http:
        google = GoogleCalendar(http, "calendar-test", "secret-factice", CALLBACK)
        query = parse_qs(urlsplit(google.authorization_url("state", "challenge")).query)
        assert set(query["scope"][0].split()) == SCOPES
        assert query["code_challenge_method"] == ["S256"]
        assert query["access_type"] == ["offline"] and query["state"] == ["state"]
        assert "client_secret" not in query
        refresh = await google.exchange("factice", "recette")
        access = await google.access(refresh)
        interval = Interval(NOW, NOW + timedelta(minutes=60))
        assert await google.busy(access, interval) == []
        event = CalendarEvent("8" * 64, "Bloc fictif", interval, "Europe/Paris")
        await google.upsert(access, event, previous=None)
        await google.upsert(access, event, previous=await google.event(access, event.id))
        assert len([req for req in requests if req.url.path.endswith("/events")]) == 1


async def test_google_patch_rejects_an_event_changed_after_reading() -> None:
    event_id = "8" * 64
    interval = Interval(NOW, NOW + timedelta(minutes=60))
    paths = []

    def transport(req: httpx.Request) -> httpx.Response:
        paths.append(req.method)
        if req.method == "GET":
            return httpx.Response(
                200,
                json={
                    "etag": '"exact-version"',
                    "summary": "Bloc initial",
                    "start": {"dateTime": interval.start.isoformat(), "timeZone": "Europe/Paris"},
                    "end": {"dateTime": interval.end.isoformat()},
                    "extendedProperties": {"private": {"tremplinEvent": event_id}},
                },
            )
        assert req.method == "PATCH"
        assert req.url.path == f"/calendar/v3/calendars/primary/events/{event_id}"
        assert req.headers["If-Match"] == '"exact-version"'
        return httpx.Response(412)

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as http:
        google = GoogleCalendar(http, "factice", "secret-factice", CALLBACK)
        old = await google.event("access", event_id)
        assert old is not None
        changed = replace(
            old,
            title="Bloc déplacé",
            period=Interval(
                interval.start + timedelta(days=1),
                interval.end + timedelta(days=1),
            ),
        )
        with pytest.raises(AppError) as error:
            await google.upsert("access", changed, previous=old)
        assert error.value.code == "calendar_conflict"
        assert paths == ["GET", "PATCH"]


async def test_partial_google_consent_is_revoked() -> None:
    def transport(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/token":
            return httpx.Response(
                200, json={"scope": sorted(SCOPES)[0], "refresh_token": "partiel"}
            )
        assert req.url.path == "/revoke" and req.content == b"token=partiel"
        return httpx.Response(200)

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as http:
        google = GoogleCalendar(http, "factice", "secret-factice", CALLBACK)
        with pytest.raises(AppError, match="renouvelée"):
            await google.exchange("factice", "recette")
