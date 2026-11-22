"""Port Agenda isolé pour les recettes synthétiques."""

from urllib.parse import urlencode

from app.providers.calendar.base import CalendarEvent, Interval, conflict, same_event, unauthorized


class FakeCalendar:
    def __init__(self, busy: list[Interval] | None = None, callback: str = "") -> None:
        self.intervals = list(busy or [])
        self.events: dict[str, CalendarEvent] = {}
        self.exchanges = self.writes = self.revocations = 0
        self.callback = callback or "/api/v1/calendar/callback"

    def authorization_url(self, state: str, challenge: str) -> str:
        return f"{self.callback}?{urlencode({'state': state, 'code': 'fake'})}"

    async def exchange(self, code: str, verifier: str) -> str:
        if code != "fake" or not verifier:
            raise unauthorized()
        self.exchanges += 1
        return "refresh-synthetique-agenda"

    async def revoke(self, refresh: str) -> None:
        self.revocations += 1

    async def access(self, refresh: str) -> str:
        return "access-synthetique"

    async def busy(self, access: str, period: Interval) -> list[Interval]:
        return [
            item for item in self.intervals if item.start < period.end and period.start < item.end
        ] + [
            event.period
            for event in self.events.values()
            if event.period.start < period.end and period.start < event.period.end
        ]

    async def event(self, access: str, event_id: str) -> CalendarEvent | None:
        return self.events.get(event_id)

    async def upsert(
        self, access: str, event: CalendarEvent, *, previous: CalendarEvent | None
    ) -> None:
        current = self.events.get(event.id)
        if current is not None and same_event(current, event):
            return
        if current != previous:
            raise conflict()
        self.events[event.id] = event
        self.writes += 1
