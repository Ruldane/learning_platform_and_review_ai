"""Un instant stable dans le créneau choisi chaque semaine locale."""

from datetime import date, datetime, timedelta
from hashlib import sha256

from app.core.clock import user_zone, week_start
from app.features.message_review.service import TelegramConnection


def _minutes(value: str) -> int:
    return int(value[:2]) * 60 + int(value[3:])


def due_week(connection: TelegramConnection, now: datetime, seed: str) -> tuple[date, date] | None:
    local = now.astimezone(user_zone(connection.timezone))
    week = week_start(local.date())
    entropy = sha256(f"{seed}/{week.isoformat()}".encode()).digest()
    day = week + timedelta(days=entropy[0] % 7)
    start, end = _minutes(connection.start), _minutes(connection.end)
    minute = start + int.from_bytes(entropy[1:4], "big") % (end - start)
    if day == local.date() and minute <= local.hour * 60 + local.minute < end:
        return week, day
    return None
