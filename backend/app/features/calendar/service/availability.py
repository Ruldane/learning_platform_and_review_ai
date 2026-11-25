"""Contiguous slots of the study day, in Tremplin's time zone."""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.features.calendar.service.oauth import credential
from app.features.calendar.service.runtime import CalendarRuntime
from app.providers.calendar.base import Interval

HORIZON_DAYS = 21
STUDY_START = time(8)
STUDY_END = time(22)


def overlaps(first: Interval, second: Interval) -> bool:
    return first.start < second.end and second.start < first.end


def study_windows(day: date, zone: ZoneInfo, busy: list[Interval], now: datetime) -> list[Interval]:
    start = datetime.combine(day, STUDY_START, zone).astimezone(UTC)
    end = datetime.combine(day, STUDY_END, zone).astimezone(UTC)
    cursor = max(start, now.astimezone(UTC))
    free = []
    for item in sorted(busy, key=lambda block: block.start):
        blocked_from, blocked_to = item.start.astimezone(UTC), item.end.astimezone(UTC)
        if blocked_to <= cursor or blocked_from >= end:
            continue
        if cursor < blocked_from:
            free.append(Interval(cursor.astimezone(zone), blocked_from.astimezone(zone)))
        cursor = max(cursor, blocked_to)
    if cursor < end:
        free.append(Interval(cursor.astimezone(zone), end.astimezone(zone)))
    return free


async def day_caps(
    rt: CalendarRuntime, user_id: str, today: date, zone: ZoneInfo, now: datetime
) -> dict[date, int]:
    async with rt.lock(user_id):
        async with rt.factory() as db:
            active = await credential(rt, db, user_id)
        if active is None:
            return {}
        port = rt.provider()
        access = await port.access(active.refresh)
        start = datetime.combine(today, STUDY_START, zone)
        end = datetime.combine(today + timedelta(days=HORIZON_DAYS - 1), STUDY_END, zone)
        busy = await port.busy(access, Interval(start, end))
    days = [today + timedelta(days=offset) for offset in range(HORIZON_DAYS)]
    return {
        day: max(
            (
                int((slot.end.astimezone(UTC) - slot.start.astimezone(UTC)).total_seconds() // 60)
                for slot in study_windows(day, zone, busy, now)
            ),
            default=0,
        )
        for day in days
    }
