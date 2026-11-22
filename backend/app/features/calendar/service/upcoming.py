"""Lecture locale du prochain événement confirmé, sans texte personnel."""

from app.features.calendar.repository import Proposals
from app.features.calendar.schemas import CalendarProposalOut, UpcomingEvent
from app.features.calendar.service.oauth import credential
from app.features.calendar.service.runtime import CalendarRuntime


async def next_event(rt: CalendarRuntime, user_id: str) -> UpcomingEvent | None:
    async with rt.factory() as db:
        active = await credential(rt, db, user_id)
        if active is None:
            return None
        row = await Proposals(db, user_id).next_confirmed(active.generation, rt.now())
        if row is None:
            return None
        preview = CalendarProposalOut.model_validate(row.payload["preview"])
    return UpcomingEvent(
        id=row.event_id,
        kind=preview.kind,
        start=preview.start,
        end=preview.end,
        timezone=preview.timezone,
    )
