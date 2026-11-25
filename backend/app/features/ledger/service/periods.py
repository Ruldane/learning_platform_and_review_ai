"""Periods and deadlines of the run ledger (P13): pure rules, in local time (D98).

A run is filed by `(user_id, name, period)`; `period` is the local day ("2026-11-16"), the local
ISO week ("2026-W47") or any other label of 16 characters at most. The days passed here are
already local days: the time zone is applied by the caller (`local_today`)."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.clock import Weekday, local_moment

RADAR_WEEKDAY: Weekday = "monday"
RADAR_TIME = "06:00"
ATS_EVERY_DAYS = 30
MAX_ATTEMPTS = 3


def day_period(day: date) -> str:
    """The period of a local day: "2026-11-16"."""
    return day.isoformat()


def week_period(day: date) -> str:
    """The period of the ISO week (Monday → Sunday) of `day`: "2026-W47". The year is that of the
    ISO week (1 January 2027 falls in "2026-W53")."""
    iso = day.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def brief_moment(day: date, hhmm: str, zone: ZoneInfo) -> datetime:
    """The UTC instant at which it is `hhmm` on the local day `day` (see
    `core.clock.local_moment`)."""
    return local_moment(day, hhmm, zone)


def is_stale(started_at: datetime, now: datetime, minutes: int = 30) -> bool:
    """True if a `running` run started more than `minutes` minutes ago: it is presumed dead and
    can be resumed."""
    return now - started_at > timedelta(minutes=minutes)
