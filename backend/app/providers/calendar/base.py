"""Accès à l’Agenda principal, limité aux occupations et aux événements Tremplin."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.core.errors import AppError


@dataclass(frozen=True)
class Interval:
    start: datetime
    end: datetime


@dataclass(frozen=True)
class CalendarEvent:
    id: str
    title: str
    period: Interval
    timezone: str
    etag: str | None = None


def same_event(first: CalendarEvent, second: CalendarEvent) -> bool:
    return (first.id, first.title, first.period) == (second.id, second.title, second.period)


def unavailable() -> AppError:
    return AppError("calendar_unavailable", "Google Calendar is temporarily unavailable.", 503)


def unauthorized() -> AppError:
    return AppError("calendar_unauthorized", "Reconnect your calendar to renew access.", 409)


def conflict() -> AppError:
    return AppError("calendar_conflict", "This time slot is no longer available.", 409)


class CalendarPort(Protocol):
    def authorization_url(self, state: str, challenge: str) -> str: ...
    async def exchange(self, code: str, verifier: str) -> str: ...
    async def revoke(self, refresh: str) -> None: ...
    async def access(self, refresh: str) -> str: ...
    async def busy(self, access: str, period: Interval) -> list[Interval]: ...
    async def event(self, access: str, event_id: str) -> CalendarEvent | None: ...
    async def upsert(
        self, access: str, event: CalendarEvent, *, previous: CalendarEvent | None
    ) -> None: ...
