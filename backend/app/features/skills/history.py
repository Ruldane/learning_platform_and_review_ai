"""Progress curve of the map (SPEC F15, D106, D107): the weekly snapshots written by the
`skill_snapshots` task (`write_weekly_snapshots`), plus the current week's point computed live
from `user_skills` (D6). Weeks run Monday to Sunday, in January's time zone (D98). Read-only,
outside `service` like `map` (cycle with `program`)."""

from collections.abc import Iterable
from datetime import date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_today, user_zone, week_start
from app.features.settings.service import SettingsService
from app.features.skills.radar import as_level, level_counts, mean_score
from app.features.skills.repository import SkillSnapshotRepository, UserSkillRepository
from app.features.skills.schemas import HistoryOut, HistoryPointOut, LevelCountsOut

DEFAULT_WEEKS = 12
MAX_WEEKS = 52


def _point(week: date, levels: Iterable[object]) -> HistoryPointOut:
    parsed = [as_level(str(value)) for value in levels]
    counts = level_counts(parsed)
    return HistoryPointOut(
        week_start=week,
        counts=LevelCountsOut(
            declared=counts["declared"],
            in_progress=counts["in_progress"],
            validated=counts["validated"],
            proven=counts["proven"],
        ),
        score=mean_score(parsed),
    )


async def skill_history(db: AsyncSession, user_id: str, weeks: int, now: datetime) -> HistoryOut:
    """One point per week among the last `weeks` (current week included), from oldest to newest; a
    week with no snapshot has no point. The snapshot of week W is written at the first pass of W:
    it is the END state of W − 1, recorded under W − 1 (re-reading 5.10 m7, final review of phase
    5). The current week's point is computed live."""
    zone = user_zone((await SettingsService(db, user_id).get()).timezone)
    current = week_start(local_today(zone, now))
    first = current - timedelta(weeks=weeks - 1)
    week = timedelta(weeks=1)
    snapshots = await SkillSnapshotRepository(db, user_id).between(first + week, current + week)
    points = [
        _point(
            snap.week_start - week, snap.levels.values() if isinstance(snap.levels, dict) else []
        )
        for snap in snapshots
    ]
    live = await UserSkillRepository(db, user_id).by_skill()
    points.append(_point(current, live.values()))
    return HistoryOut(points=points)
