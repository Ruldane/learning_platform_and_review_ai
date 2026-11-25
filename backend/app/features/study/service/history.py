"""History of completed study time, brought back to the user's local days."""

from collections import Counter
from dataclasses import dataclass
from datetime import date
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_today
from app.features.study.repository import StudyRepository


@dataclass(frozen=True)
class StudyHistory:
    first_day: date | None
    daily_minutes: tuple[tuple[date, int], ...]


async def finished_history(
    db: AsyncSession, user_id: str, *, zone: ZoneInfo, since: date, before: date
) -> StudyHistory:
    """The first day observed before `before` and the minutes over `[since, before[`."""
    first = None
    minutes: Counter[date] = Counter()
    for ended_at, worked in await StudyRepository(db, user_id).finished():
        day = local_today(zone, ended_at)
        if day >= before:
            continue
        if first is None or day < first:
            first = day
        if day >= since:
            minutes[day] += worked
    return StudyHistory(first, tuple(sorted(minutes.items())))
