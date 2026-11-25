"""The activity feed (P15, D163): the merge of the `ACTIVITY_SOURCES`, most recent first. No
table, no write. Total order `(at, id)` descending; **the cursor is an `(at, id)` pair**: two
events at the same instant are therefore lost neither at the cut of a page (`before`) nor at the
boundary of a re-read (`after`). Sources receive **inclusive** bounds and return their most
recent events; the feed itself discards what the cursor excludes, and asks a source for more when
it may have been truncated by its ties. A source that fails is dropped, the rest of the feed is
returned (log: the source name and the exception class only)."""

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.activity.schemas import ActivityItem, ActivityPage
from app.features.activity.service.sources import ACTIVITY_SOURCES, ActivitySource

logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 30
MAX_LIMIT = 50
MAX_FETCH = 400  # a source never returns more rows than this (extreme ties)

Cursor = tuple[datetime | None, str | None]


def _inside(item: ActivityItem, after: Cursor, before: Cursor) -> bool:
    """Is the event inside the window? Without `id`, the bound is exclusive on the instant;
    with `id`, it is the `(at, id)` pair that is strictly beyond the cursor."""
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
    """The first `limit` events of the window for one source; empty if it fails. The savepoint
    keeps the transaction valid for the following sources after an SQL error."""
    fetch = limit
    while True:
        try:
            async with db.begin_nested():
                raw = await source(db, user_id, after[0], before[0], fetch)
        except Exception as exc:
            logger.warning(
                "Activity feed: source %s failed (%s)", source.__name__, type(exc).__name__
            )
            return []
        kept = [item for item in raw if _inside(item, after, before)]
        if len(raw) < fetch or len(kept) >= limit or fetch >= MAX_FETCH:
            return kept
        fetch = min(fetch * 2, MAX_FETCH)  # source possibly truncated by discarded ties


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
    """The events between the cursors `(after, after_id)` and `(before, before_id)`, at most
    `limit` (1 to 50). `after` alone: more recent than this instant; with `after_id`: more recent
    than this event (the next one at the same instant included). Same for `before`, going older."""
    limit = min(max(limit, 1), MAX_LIMIT)
    merged: dict[str, ActivityItem] = {}
    for source in ACTIVITY_SOURCES:
        for item in await _read(db, user_id, source, (after, after_id), (before, before_id), limit):
            merged.setdefault(item.id, item)
    items = sorted(merged.values(), key=lambda item: (item.at, item.id), reverse=True)[:limit]
    return ActivityPage(items=items, latest_at=items[0].at if items else None)
