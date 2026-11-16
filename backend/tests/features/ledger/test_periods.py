"""Périodes et échéances du registre des passages (8.1, P13) : règles pures, en heure locale."""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.clock import local_today
from app.features.ledger.service.periods import (
    ATS_EVERY_DAYS,
    MAX_ATTEMPTS,
    RADAR_TIME,
    RADAR_WEEKDAY,
    brief_moment,
    day_period,
    is_stale,
    week_period,
)

PARIS = ZoneInfo("Europe/Paris")


def test_constants() -> None:
    assert (RADAR_WEEKDAY, RADAR_TIME, ATS_EVERY_DAYS, MAX_ATTEMPTS) == ("monday", "06:00", 30, 3)


def test_day_period() -> None:
    assert day_period(date(2026, 11, 16)) == "2026-11-16"
    assert day_period(date(2026, 1, 5)) == "2026-01-05"


def test_week_period_is_iso_and_padded() -> None:
    assert week_period(date(2026, 11, 16)) == "2026-W47"  # lundi
    assert week_period(date(2026, 11, 22)) == "2026-W47"  # dimanche
    assert week_period(date(2026, 1, 5)) == "2026-W02"  # deux chiffres


def test_week_period_uses_the_iso_year_at_the_turn() -> None:
    assert week_period(date(2026, 12, 31)) == "2026-W53"
    assert week_period(date(2027, 1, 1)) == "2026-W53"
    assert week_period(date(2027, 1, 4)) == "2027-W01"


def test_week_period_local_sunday_night() -> None:
    # Lundi 00 h 30 à Paris = dimanche 23 h 30 UTC : la semaine est celle du lundi local.
    now = datetime(2026, 11, 22, 23, 30, tzinfo=UTC)
    assert week_period(now.date()) == "2026-W47"
    assert week_period(local_today(PARIS, now)) == "2026-W48"


def test_brief_moment_is_utc() -> None:
    moment = brief_moment(date(2026, 11, 16), "07:00", PARIS)
    assert moment == datetime(2026, 11, 16, 6, 0, tzinfo=UTC)
    assert moment.utcoffset() == timedelta(0)


def test_brief_moment_on_dst_day() -> None:
    assert brief_moment(date(2026, 3, 29), "07:00", PARIS) == datetime(
        2026, 3, 29, 5, 0, tzinfo=UTC
    )
    assert brief_moment(date(2026, 10, 25), "07:00", PARIS) == datetime(
        2026, 10, 25, 6, 0, tzinfo=UTC
    )


def test_is_stale_after_thirty_minutes() -> None:
    now = datetime(2026, 11, 16, 9, 0, tzinfo=UTC)
    assert not is_stale(now - timedelta(minutes=29), now)
    assert not is_stale(now - timedelta(minutes=30), now)
    assert is_stale(now - timedelta(minutes=30, seconds=1), now)
    assert is_stale(now - timedelta(minutes=5), now, minutes=4)
    assert not is_stale(now + timedelta(minutes=5), now)  # début dans le futur
