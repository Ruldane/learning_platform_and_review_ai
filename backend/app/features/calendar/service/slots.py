"""Le créneau retenu est exprimé dans le fuseau IANA choisi dans Tremplin."""

from datetime import UTC, datetime, time, timedelta

from app.core.errors import AppError
from app.features.calendar.schemas import InterviewSelection
from app.features.calendar.service.availability import STUDY_END, STUDY_START, study_windows
from app.features.calendar.service.sources import Source
from app.providers.calendar.base import CalendarEvent, CalendarPort, Interval, conflict


def interview_period(source: Source, selection: InterviewSelection, now: datetime) -> Interval:
    wall = datetime.combine(source.day, time.fromisoformat(selection.time))
    start = wall.replace(tzinfo=source.zone)
    instant = start.astimezone(UTC)
    if (
        instant.astimezone(source.zone).replace(tzinfo=None) != wall
        or start.utcoffset() != start.replace(fold=1).utcoffset()
    ):
        raise AppError(
            "calendar_ambiguous_time", "Choisis une heure locale sans changement d’heure.", 422
        )
    if instant < now:
        raise conflict()
    end = (instant + timedelta(minutes=source.minutes)).astimezone(source.zone)
    return Interval(start, end)


async def study_period(
    port: CalendarPort, access: str, source: Source, now: datetime, old: CalendarEvent | None
) -> Interval:
    duration = timedelta(minutes=source.minutes)
    bounds = Interval(
        datetime.combine(source.day, STUDY_START, source.zone),
        datetime.combine(source.day, STUDY_END, source.zone),
    )
    if old:
        start, end = (i.astimezone(UTC) for i in (old.period.start, old.period.end))
        if bounds.start <= start and start >= now and end <= bounds.end and end - start == duration:
            return Interval(start.astimezone(source.zone), end.astimezone(source.zone))
    if now.second or now.microsecond:
        now = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
    if now >= bounds.end:
        raise conflict()
    busy = await port.busy(access, bounds)
    for slot in study_windows(source.day, source.zone, busy, now):
        start = slot.start.astimezone(UTC)
        end = (start + duration).astimezone(source.zone)
        if end <= slot.end:
            return Interval(slot.start, end)
    raise conflict()
