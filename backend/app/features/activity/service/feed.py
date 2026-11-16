"""Le fil d'activité (P15, D163) : la fusion des `ACTIVITY_SOURCES`, la plus récente d'abord. Aucune
table, aucun journal : rien de ce fil n'est écrit ni gardé. Un événement rendu deux fois (même
`id`) ne l'est qu'une."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.activity.schemas import ActivityItem, ActivityPage
from app.features.activity.service.sources import ACTIVITY_SOURCES

DEFAULT_LIMIT = 30
MAX_LIMIT = 50


async def activity_page(
    db: AsyncSession,
    user_id: str,
    *,
    after: datetime | None,
    before: datetime | None,
    limit: int = DEFAULT_LIMIT,
) -> ActivityPage:
    """Les événements dans `]after, before[`, `limit` au plus (1 à 50). Chaque source donne ses
    `limit` plus récents : la fusion n'en perd aucun parmi les `limit` premiers."""
    limit = min(max(limit, 1), MAX_LIMIT)
    merged: dict[str, ActivityItem] = {}
    for source in ACTIVITY_SOURCES:
        for item in await source(db, user_id, after, before, limit):
            merged.setdefault(item.id, item)
    items = sorted(merged.values(), key=lambda item: (item.at, item.id), reverse=True)[:limit]
    return ActivityPage(items=items, latest_at=items[0].at if items else None)
