"""Temps local de January (D98) : le back tourne en UTC, les jours et les semaines se comptent
dans son fuseau."""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from app.core.clock import (
    DEFAULT_ZONE,
    WEEKDAYS,
    is_zone,
    local_moment,
    local_today,
    user_zone,
    week_start,
)

PARIS = "Europe/Paris"


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        ("2026-11-15T23:30:00+00:00", date(2026, 11, 16)),
        ("2026-11-15T22:59:00+00:00", date(2026, 11, 15)),
    ],
)
def test_local_today_crosses_midnight_in_paris(now: str, expected: date) -> None:
    assert local_today(user_zone(PARIS), datetime.fromisoformat(now)) == expected


def test_local_today_reads_a_naive_moment_as_utc() -> None:
    assert local_today(user_zone(PARIS), datetime(2026, 11, 15, 23, 30)) == date(2026, 11, 16)


def test_local_today_defaults_to_now() -> None:
    zone = user_zone(PARIS)
    before = datetime.now(UTC).astimezone(zone).date()
    today = local_today(zone)
    assert today in {before, datetime.now(UTC).astimezone(zone).date()}


def test_local_moment_sunday_18h_paris_is_17h_utc_in_winter() -> None:
    moment = local_moment(date(2026, 11, 15), "18:00", user_zone(PARIS))
    assert moment.hour == 17 and moment.utcoffset() is not None
    assert moment == datetime(2026, 11, 15, 17, 0, tzinfo=UTC)


def test_local_moment_on_dst_sunday() -> None:  # 2027-03-28, passage à l'heure d'été
    assert local_moment(date(2027, 3, 28), "18:00", user_zone(PARIS)).hour == 16


def test_week_start_is_monday() -> None:
    assert week_start(date(2026, 11, 15)) == date(2026, 11, 9)
    assert week_start(date(2026, 11, 16)) == date(2026, 11, 16)


def test_unknown_zone_falls_back_to_paris() -> None:
    assert DEFAULT_ZONE == PARIS
    for name in ("Mars/Olympus", "", "../etc/passwd", "/etc/localtime"):
        assert user_zone(name) == ZoneInfo(PARIS)
        assert not is_zone(name)
    assert is_zone("America/New_York") and is_zone("UTC")


def test_weekdays_monday_to_sunday() -> None:
    assert list(WEEKDAYS.items()) == [
        ("monday", 0),
        ("tuesday", 1),
        ("wednesday", 2),
        ("thursday", 3),
        ("friday", 4),
        ("saturday", 5),
        ("sunday", 6),
    ]
