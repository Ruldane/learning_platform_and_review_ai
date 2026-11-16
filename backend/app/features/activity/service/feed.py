"""Le fil d'activité (P15, D163) : la fusion des `ACTIVITY_SOURCES`, la plus récente d'abord. Aucune
table, aucun écrit. Ordre total `(at, id)` décroissant ; **le curseur est un couple `(at, id)`** :
deux événements au même instant ne se perdent donc ni à la coupure d'une page (`before`), ni à la
frontière d'une relecture (`after`). Les sources reçoivent des bornes **incluses** et rendent leurs
plus récents ; le fil écarte lui-même ce que le curseur exclut, et redemande plus à une source qui
a pu être tronquée par ses ex æquo. Une source qui échoue est écartée, le reste du fil est rendu
(journal : nom de la source et classe de l'exception seulement)."""

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.activity.schemas import ActivityItem, ActivityPage
from app.features.activity.service.sources import ACTIVITY_SOURCES, ActivitySource

logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 30
MAX_LIMIT = 50
MAX_FETCH = 400  # une source ne rend jamais plus de lignes (ex æquo extrêmes)

Cursor = tuple[datetime | None, str | None]


def _inside(item: ActivityItem, after: Cursor, before: Cursor) -> bool:
    """L'événement est-il dans la fenêtre ? Sans `id`, la borne est exclusive sur l'instant ;
    avec `id`, c'est le couple `(at, id)` qui est strictement au-delà du curseur."""
    key = (item.at, item.id)
    after_at, after_id = after
    if after_at is not None:
        if after_id is None:
            if item.at <= after_at:
                return False
        elif key <= (after_at, after_id):
            return False
    before_at, before_id = before
    if before_at is not None:
        if before_id is None:
            if item.at >= before_at:
                return False
        elif key >= (before_at, before_id):
            return False
    return True


async def _read(
    db: AsyncSession,
    user_id: str,
    source: ActivitySource,
    after: Cursor,
    before: Cursor,
    limit: int,
) -> list[ActivityItem]:
    """Les `limit` premiers événements de la fenêtre pour une source ; vide si elle échoue. Le
    savepoint garde la transaction valide pour les sources suivantes après une erreur SQL."""
    fetch = limit
    while True:
        try:
            async with db.begin_nested():
                raw = await source(db, user_id, after[0], before[0], fetch)
        except Exception as exc:
            logger.warning(
                "Fil d'activité : source %s en échec (%s)", source.__name__, type(exc).__name__
            )
            return []
        kept = [item for item in raw if _inside(item, after, before)]
        if len(raw) < fetch or len(kept) >= limit or fetch >= MAX_FETCH:
            return kept
        fetch = min(fetch * 2, MAX_FETCH)  # source peut-être tronquée par des ex æquo écartés


async def activity_page(
    db: AsyncSession,
    user_id: str,
    *,
    after: datetime | None,
    before: datetime | None,
    after_id: str | None = None,
    before_id: str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> ActivityPage:
    """Les événements entre les curseurs `(after, after_id)` et `(before, before_id)`, `limit` au
    plus (1 à 50). `after` seul : plus récents que cet instant ; avec `after_id` : plus récents que
    cet événement (le suivant au même instant compris). Même chose pour `before` vers l'ancien."""
    limit = min(max(limit, 1), MAX_LIMIT)
    merged: dict[str, ActivityItem] = {}
    for source in ACTIVITY_SOURCES:
        for item in await _read(db, user_id, source, (after, after_id), (before, before_id), limit):
            merged.setdefault(item.id, item)
    items = sorted(merged.values(), key=lambda item: (item.at, item.id), reverse=True)[:limit]
    return ActivityPage(items=items, latest_at=items[0].at if items else None)
