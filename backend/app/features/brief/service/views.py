"""Reading the daily brief (14.2, D162): the brief returned by the API, with an up-to-date advice
status. A `pending` advice whose session is no longer open (failure, cancellation, restart without
resume, lost session) becomes `failed` on read: the status follows the session, like the radar
run. `failed` and `unavailable` are final for the day (the port ignores any later write): the
front end has no "Retry" to offer. Logs: ids only."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.daily import Brief
from app.features.brief.repository import BriefRepository
from app.features.brief.schemas import BriefOut
from app.features.brief.service.runtime import GRAPH, SUBJECT, BriefRuntime
from app.features.reading_stack.service.entries import unread_count
from app.features.sessions.service import list_open_sessions_by_subject

logger = logging.getLogger(__name__)

# Time allowed to launch the session after creation: with no session beyond it, the launch was
# interrupted (process stopped) and the advice will not come.
LAUNCH_GRACE = timedelta(minutes=5)


def brief_not_found() -> AppError:
    return AppError("brief_not_found", "Brief not found.", 404)


def out_of(row: Brief) -> BriefOut:
    """The returned brief: `resource` stored empty (`{}`) or absent = `None`, the advice is the list
    of its two sentences. Internal section details (`key`, `best_quiz`) are ignored."""
    sections: dict[str, Any] = row.sections
    advice = (row.advice or {}).get("sentences")
    return BriefOut.model_validate(
        {
            "id": row.id,
            "day": row.day,
            "origin": row.origin,
            "generated_at": row.created_at,
            "block": sections.get("block"),
            "reviews": sections["reviews"],
            "reminders": sections["reminders"],
            "offers": sections["offers"],
            "week": sections.get("week"),
            "resource": row.resource or None,
            "unavailable": sections.get("unavailable", []),
            "advice": advice,
            "advice_status": row.advice_status,
            "session_id": row.session_id,
        }
    )


async def _session_is_dead(rt: BriefRuntime, db: AsyncSession, user_id: str, row: Brief) -> bool:
    if row.session_id is None:
        return rt.now() - row.created_at > LAUNCH_GRACE
    open_ids = await list_open_sessions_by_subject(db, user_id, graph=GRAPH, subject_type=SUBJECT)
    return row.session_id not in open_ids.get(row.id, [])


async def settle(rt: BriefRuntime, db: AsyncSession, user_id: str, row: Brief) -> None:
    """A `pending` advice without an open session becomes `failed`. The session is read BEFORE
    the write, which only changes what is still `pending`: an advice stored in the meantime stays
    `ready`."""
    if row.advice_status != "pending" or not await _session_is_dead(rt, db, user_id, row):
        return
    if await BriefRepository(db, user_id).close_advice(row.id, "failed"):
        await db.commit()
        logger.info("Brief without a session: user %s, brief %s", user_id, row.id)


async def brief_out(rt: BriefRuntime, db: AsyncSession, user_id: str, brief_id: str) -> BriefOut:
    repo = BriefRepository(db, user_id)
    row = await repo.get_fresh(brief_id)
    if row is None:
        raise brief_not_found()
    if row.advice_status == "pending":
        await settle(rt, db, user_id, row)
        row = await repo.get_fresh(brief_id) or row
    return out_of(row).model_copy(update={"reading_unread": await unread_count(db, user_id)})


@dataclass(frozen=True)
class RecentBrief:
    id: str
    at: datetime


async def recent_briefs(
    db: AsyncSession, user_id: str, after: datetime | None, before: datetime | None, limit: int
) -> list[RecentBrief]:
    """Briefs created within `[after, before]`, most recent first (activity feed, 8.7)."""
    rows = await BriefRepository(db, user_id).created_between(after, before, limit)
    return [RecentBrief(id=row.id, at=row.created_at) for row in rows]
