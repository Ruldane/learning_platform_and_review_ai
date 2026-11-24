"""January's local time (D98): the back runs in UTC, but her days and weeks (Monday ->
Sunday), her streak, her cards' due dates and her review are counted in her time zone
(`UserSettings.timezone`). Every day or week computation goes through here.

Time zone data comes from the system, otherwise from the `tzdata` package, declared as a
dependency so it is never missing (`python:*-slim` image, Windows)."""

from datetime import UTC, date, datetime, time, timedelta
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

Weekday = Literal["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
WEEKDAYS: dict[Weekday, int] = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}
DEFAULT_ZONE = "Europe/Paris"
_ENGLISH_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def english_day(day: date, *, include_year: bool = True) -> str:
    """Render a calendar date in English independently of the server's locale."""
    year = f" {day.year}" if include_year else ""
    return f"{day.day} {_ENGLISH_MONTHS[day.month - 1]}{year}"


def _load(name: str) -> ZoneInfo | None:
    """The IANA time zone `name`, or `None` if unknown or malformed (path, empty...)."""
    if not name or name.startswith("/"):
        return None
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        return None


def is_zone(name: str) -> bool:
    """True if `name` is a known IANA time zone."""
    return _load(name) is not None


def user_zone(name: str) -> ZoneInfo:
    """January's time zone; an unknown name gives `Europe/Paris`."""
    return _load(name) or ZoneInfo(DEFAULT_ZONE)


def local_today(zone: ZoneInfo, now: datetime | None = None) -> date:
    """January's day at instant `now` (now by default; without a time zone: UTC)."""
    moment = now or datetime.now(UTC)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(zone).date()


def week_start(day: date) -> date:
    """The Monday of `day`'s week."""
    return day - timedelta(days=day.weekday())


def local_moment(day: date, hhmm: str, zone: ZoneInfo) -> datetime:
    """The UTC instant (time-zone aware) when it is `hhmm` ("18:00") on `day` for January.

    An hour skipped at the switch to summer time is read with the offset from before (the
    `zoneinfo` rule, `fold=0`)."""
    hours, minutes = (int(part) for part in hhmm.split(":"))
    return datetime.combine(day, time(hours, minutes), tzinfo=zone).astimezone(UTC)
