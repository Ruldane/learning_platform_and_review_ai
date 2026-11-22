from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.features.calendar.service.availability import study_windows
from app.providers.calendar.base import Interval


def test_windows_clip_merge_and_use_local_day_after_summer_time() -> None:
    day = date(2026, 10, 26)
    now = datetime(2026, 10, 26, 6, tzinfo=UTC)
    busy = [
        Interval(now + timedelta(hours=2), now + timedelta(hours=5)),
        Interval(now + timedelta(hours=4), now + timedelta(hours=10)),
    ]
    result = study_windows(day, ZoneInfo("Europe/Paris"), busy, now)
    assert [(slot.start.hour, slot.end.hour) for slot in result] == [(8, 9), (17, 22)]
    assert all(slot.start.utcoffset() == timedelta(hours=1) for slot in result)
