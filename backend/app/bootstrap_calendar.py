"""Wiring without network access before consent."""

from contextlib import AsyncExitStack
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI

from app.config import Settings
from app.features.calendar.service.oauth import COOKIE_PATH
from app.features.calendar.service.runtime import CalendarRuntime
from app.providers.calendar.base import CalendarPort
from app.providers.calendar.google import GoogleCalendar
from app.providers.web.fetch import refuse_all_cookies


def _valid_callback(uri: str) -> bool:
    try:
        parsed = urlsplit(uri)
        return (
            parsed.path == COOKIE_PATH
            and not parsed.query
            and not parsed.fragment
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
            and (
                parsed.scheme == "https"
                or (parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1"})
            )
        )
    except ValueError:
        return False


async def open_calendar(app: FastAPI, stack: AsyncExitStack) -> CalendarRuntime:
    settings: Settings = app.state.settings
    port: CalendarPort | None = getattr(app.state, "injected_calendar", None)
    client_id = settings.calendar_google_client_id
    secret = settings.calendar_google_client_secret
    redirect = settings.calendar_google_redirect_uri or ""
    if (
        port is None
        and settings.calendar_google_dedicated_project
        and client_id
        and client_id != settings.google_client_id
        and secret
        and secret.get_secret_value()
        and _valid_callback(redirect)
    ):
        http = await stack.enter_async_context(
            httpx.AsyncClient(
                timeout=10.0, trust_env=False, follow_redirects=False, cookies=refuse_all_cookies()
            )
        )
        port = GoogleCalendar(http, client_id, secret.get_secret_value(), redirect)
    return CalendarRuntime(
        app.state.session_factory, app.state.cipher, port, secure=redirect.startswith("https://")
    )
