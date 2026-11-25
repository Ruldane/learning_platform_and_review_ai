"""A record's timeline (SPEC 6.1, D139): a status change or a note, dated. The status only
changes here (never by `PATCH`). A status change sets the `on_status` dates (7.1); moving to
"Applied" freezes the CV version sent. Under the applications lock. Logs: ids and statuses
only, never a note."""

import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_moment, local_today
from app.db.models.applications import Application
from app.features.applications.repository import EventRepository
from app.features.applications.schemas import ApplicationDetail, EventIn
from app.features.applications.service.adopt import freeze_version
from app.features.applications.service.reminder_sync import sync_user
from app.features.applications.service.rules import on_status
from app.features.applications.service.runtime import ApplicationsRuntime
from app.features.applications.service.views import detail_out, get_application, invalid, view_of
from app.features.postings.service.duplicates import zone_of

logger = logging.getLogger(__name__)


def event_moment(day: date, today: date, now: datetime, zone: ZoneInfo) -> datetime:
    """The timeline instant: now for today, noon (January's time) for another day, which places
    the event on its date without an invented time."""
    return now if day == today else local_moment(day, "12:00", zone)


async def change_status(
    db: AsyncSession,
    user_id: str,
    row: Application,
    body: EventIn,
    when: tuple[date, datetime, ZoneInfo],
) -> None:
    """Applies the new status: `on_status` dates, given interview day, version frozen on the
    first exit from "To apply" (except toward "Withdrawn"), `status` event. No effect if the
    status does not change."""
    assert body.status is not None
    day, at, zone = when
    old = row.status
    if body.status == old:
        return
    leaves_to_apply = body.status not in ("to_apply", "withdrawn") and (
        old == "to_apply" or (body.status == "applied" and row.applied_on is None)
    )
    effects = on_status(view_of(row, zone), body.status, day).fields()
    for name, value in effects.items():
        setattr(row, name, value)
    if body.status == "interview" and body.interview_on is not None:
        row.interview_on = body.interview_on
    row.status = body.status
    await EventRepository(db, user_id).add(
        application_id=row.id,
        kind="status",
        at=at,
        status_from=old,
        status_to=body.status,
        text=body.text,
    )
    if leaves_to_apply:
        await freeze_version(db, user_id, row, at)
    logger.info("Status changed: user %s, record %s, %s to %s", user_id, row.id, old, body.status)


async def add_event(
    rt: ApplicationsRuntime, user_id: str, application_id: str, body: EventIn
) -> ApplicationDetail:
    """Adds the event to the timeline. 404 `application_not_found`; 422 `status` (change without
    status), `text` (empty note) or `on` (future day, January's), without echo."""
    if body.kind == "status" and body.status is None:
        raise invalid("status")
    if body.kind == "note" and not body.text:
        raise invalid("text")
    async with rt.lock(user_id), rt.session_factory() as db:
        row = await get_application(db, user_id, application_id)
        zone = await zone_of(db, user_id)
        now = rt.now()
        today = local_today(zone, now)
        if body.on is not None and body.on > today:
            raise invalid("on")  # an event does not happen in the future (January's day)
        day = body.on or today
        at = event_moment(day, today, now, zone)
        if body.kind == "status":
            await change_status(db, user_id, row, body, (day, at, zone))
        else:
            await EventRepository(db, user_id).add(
                application_id=row.id, kind="note", at=at, text=body.text
            )
        row.updated_at = now
        await sync_user(db, user_id, today, application_id=row.id)
        await db.commit()
        return await detail_out(db, user_id, row, today)
