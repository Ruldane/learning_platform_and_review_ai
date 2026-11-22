"""OAuth d’Agenda et opérations ciblées sur le calendrier principal."""

from datetime import datetime
from typing import Any
from urllib.parse import urlencode

import httpx

from app.providers.calendar.base import (
    CalendarEvent,
    Interval,
    conflict,
    same_event,
    unauthorized,
    unavailable,
)

SCOPES = frozenset(
    {
        "https://www.googleapis.com/auth/calendar.freebusy",
        "https://www.googleapis.com/auth/calendar.events.owned",
    }
)
_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN = "https://oauth2.googleapis.com/token"
_REVOKE = "https://oauth2.googleapis.com/revoke"
_CALENDAR = "https://www.googleapis.com/calendar/v3"
_EVENTS = f"{_CALENDAR}/calendars/primary/events"
_MARKER = "tremplinEvent"


def _json(response: httpx.Response) -> dict[str, Any]:
    try:
        value = response.json()
    except ValueError:
        raise unavailable() from None
    if not isinstance(value, dict):
        raise unavailable()
    return value


def _date(value: str) -> datetime:
    result = datetime.fromisoformat(value)
    if result.utcoffset() is None:
        raise ValueError("Date sans fuseau")
    return result


class GoogleCalendar:
    def __init__(
        self, http: httpx.AsyncClient, client_id: str, secret: str, redirect_uri: str
    ) -> None:
        self.http, self.client_id, self.secret, self.redirect_uri = (
            http,
            client_id,
            secret,
            redirect_uri,
        )

    def authorization_url(self, state: str, challenge: str) -> str:
        query = urlencode(
            {
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "response_type": "code",
                "scope": " ".join(sorted(SCOPES)),
                "access_type": "offline",
                "prompt": "consent",
                "state": state,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
        )
        return f"{_AUTH}?{query}"

    async def _request(
        self,
        method: str,
        url: str,
        *,
        access: str | None = None,
        if_match: str | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        headers = {"Authorization": f"Bearer {access}"} if access is not None else {}
        if if_match is not None:
            headers["If-Match"] = if_match
        try:
            return await self.http.request(method, url, headers=headers, **kwargs)
        except httpx.HTTPError:
            raise unavailable() from None

    @staticmethod
    def _require(response: httpx.Response) -> None:
        if response.status_code in (401, 403):
            raise unauthorized()
        if not response.is_success:
            raise unavailable()

    async def _token(self, **grant: str) -> dict[str, Any]:
        response = await self._request(
            "POST",
            _TOKEN,
            data={
                "client_id": self.client_id,
                "client_secret": self.secret,
                **grant,
            },
        )
        if response.status_code == 400 and _json(response).get("error") == "invalid_grant":
            raise unauthorized()
        self._require(response)
        return _json(response)

    async def exchange(self, code: str, verifier: str) -> str:
        data = await self._token(
            grant_type="authorization_code",
            code=code,
            code_verifier=verifier,
            redirect_uri=self.redirect_uri,
        )
        scopes, refresh = data.get("scope"), data.get("refresh_token")
        if not isinstance(scopes, str) or frozenset(scopes.split()) != SCOPES:
            if isinstance(refresh, str) and refresh:
                await self.revoke(refresh)
            raise unauthorized()
        if not isinstance(refresh, str) or not refresh:
            raise unauthorized()
        return refresh

    async def access(self, refresh: str) -> str:
        data = await self._token(grant_type="refresh_token", refresh_token=refresh)
        scopes, token = data.get("scope"), data.get("access_token")
        if scopes is not None and (
            not isinstance(scopes, str) or frozenset(scopes.split()) != SCOPES
        ):
            raise unauthorized()
        if not isinstance(token, str) or not token:
            raise unauthorized()
        return token

    async def revoke(self, refresh: str) -> None:
        response = await self._request("POST", _REVOKE, data={"token": refresh})
        if response.status_code == 400 and _json(response).get("error") == "invalid_token":
            return
        self._require(response)

    async def busy(self, access: str, period: Interval) -> list[Interval]:
        response = await self._request(
            "POST",
            f"{_CALENDAR}/freeBusy",
            access=access,
            json={
                "timeMin": period.start.isoformat(),
                "timeMax": period.end.isoformat(),
                "timeZone": "UTC",
                "items": [{"id": "primary"}],
            },
        )
        self._require(response)
        try:
            calendars = _json(response)["calendars"]
            if not isinstance(calendars, dict) or len(calendars) != 1:
                raise ValueError("Agenda principal indisponible")
            calendar = next(iter(calendars.values()))
            if calendar.get("errors"):
                raise ValueError("Disponibilité indisponible")
            return [Interval(_date(item["start"]), _date(item["end"])) for item in calendar["busy"]]
        except (KeyError, TypeError, ValueError, AttributeError):
            raise unavailable() from None

    async def event(self, access: str, event_id: str) -> CalendarEvent | None:
        response = await self._request("GET", f"{_EVENTS}/{event_id}", access=access)
        if response.status_code == 404:
            return None
        self._require(response)
        data = _json(response)
        try:
            if data.get("extendedProperties", {}).get("private", {}).get(_MARKER) != event_id:
                raise conflict()
            start, end = data["start"], data["end"]
            etag = data.get("etag")
            return CalendarEvent(
                event_id,
                data["summary"],
                Interval(_date(start["dateTime"]), _date(end["dateTime"])),
                start.get("timeZone") or "UTC",
                etag if isinstance(etag, str) else None,
            )
        except (KeyError, TypeError, ValueError, AttributeError):
            raise conflict() from None

    @staticmethod
    def _body(event: CalendarEvent) -> dict[str, Any]:
        return {
            "summary": event.title,
            "start": {"dateTime": event.period.start.isoformat(), "timeZone": event.timezone},
            "end": {"dateTime": event.period.end.isoformat(), "timeZone": event.timezone},
            "extendedProperties": {"private": {_MARKER: event.id}},
        }

    async def upsert(
        self, access: str, event: CalendarEvent, *, previous: CalendarEvent | None
    ) -> None:
        if previous is not None and same_event(previous, event):
            return
        payload = self._body(event)
        options = {"sendUpdates": "none"}
        if previous is None:
            response = await self._request(
                "POST",
                _EVENTS,
                access=access,
                params=options,
                json={"id": event.id, "visibility": "private", **payload},
            )
            if response.status_code != 409:
                self._require(response)
                return
            current = await self.event(access, event.id)
            if current is not None and same_event(current, event):
                return
            raise conflict()
        etag = previous.etag
        if not etag or not (etag.startswith('"') and etag.endswith('"')):
            raise unavailable()
        response = await self._request(
            "PATCH",
            f"{_EVENTS}/{event.id}",
            access=access,
            if_match=etag,
            params=options,
            json=payload,
        )
        if response.status_code in (404, 412):
            raise conflict()
        self._require(response)
