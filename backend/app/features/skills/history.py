"""Courbe de progression de la carte (SPEC F15, D106, D107) : les relevés hebdomadaires écrits
par la tâche `skill_snapshots` (`write_weekly_snapshots`), plus le point de la semaine en cours
calculé en direct depuis `user_skills` (D6). Semaines du lundi au dimanche, dans le fuseau de
January (D98). Lecture seule, hors de `service` comme `map` (cycle avec `program`)."""

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
            declare=counts["declare"],
            en_cours=counts["en_cours"],
            valide=counts["valide"],
            prouve=counts["prouve"],
        ),
        score=mean_score(parsed),
    )


async def skill_history(db: AsyncSession, user_id: str, weeks: int, now: datetime) -> HistoryOut:
    """Un point par semaine relevée parmi les `weeks` dernières (semaine en cours comprise),
    du plus ancien au plus récent ; une semaine sans relevé n'a pas de point. Le point de la
    semaine en cours est toujours calculé en direct (son relevé, s'il existe, est ignoré)."""
    zone = user_zone((await SettingsService(db, user_id).get()).timezone)
    current = week_start(local_today(zone, now))
    first = current - timedelta(weeks=weeks - 1)
    snapshots = await SkillSnapshotRepository(db, user_id).between(first, current)
    points = [
        _point(snap.week_start, snap.levels.values() if isinstance(snap.levels, dict) else [])
        for snap in snapshots
    ]
    live = await UserSkillRepository(db, user_id).by_skill()
    points.append(_point(current, live.values()))
    return HistoryOut(points=points)
