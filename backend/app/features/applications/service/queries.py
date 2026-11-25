"""Application reads (SPEC 6.1, 6.4, D139): list (newest creation first), full record,
indicators. The list and the indicators first adopt the CV versions that are ready
(`adopt`, SPEC 6.1 no. 1)."""

from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_today
from app.features.applications.repository import ApplicationRepository
from app.features.applications.schemas import ApplicationDetail, ApplicationOut, ApplicationStatsOut
from app.features.applications.service.adopt import adopt
from app.features.applications.service.rules import stats
from app.features.applications.service.runtime import ApplicationsRuntime
from app.features.applications.service.views import (
    application_outs,
    detail_out,
    get_application,
    views_of,
)
from app.features.postings.service.duplicates import zone_of


async def today_of(db: AsyncSession, user_id: str, now: datetime) -> date:
    """January's day at the instant `now` (their time zone)."""
    return local_today(await zone_of(db, user_id), now)


async def list_applications(
    rt: ApplicationsRuntime,
    db: AsyncSession,
    user_id: str,
    *,
    status: str | None = None,
    posting_id: str | None = None,
) -> list[ApplicationOut]:
    """The records, most recent first; the ready versions are adopted first."""
    await adopt(rt, user_id)
    today = local_today(await zone_of(db, user_id), rt.now())
    rows = await ApplicationRepository(db, user_id).recent(status=status, posting_id=posting_id)
    return await application_outs(db, user_id, rows, today)


async def read_application(
    db: AsyncSession, user_id: str, now: datetime, application_id: str
) -> ApplicationDetail:
    row = await get_application(db, user_id, application_id)
    return await detail_out(db, user_id, row, local_today(await zone_of(db, user_id), now))


async def read_stats(
    rt: ApplicationsRuntime, db: AsyncSession, user_id: str
) -> ApplicationStatsOut:
    """Records by status, rate and average response delay, reminders due (SPEC 6.4)."""
    await adopt(rt, user_id)
    zone = await zone_of(db, user_id)
    repo = ApplicationRepository(db, user_id)
    due = sum((await repo.due_counts(local_today(zone, rt.now()))).values())
    result = stats(await views_of(db, user_id, zone), due)
    return ApplicationStatsOut(
        by_status=result.by_status,
        response_rate=result.response_rate,
        mean_response_days=result.mean_response_days,
        due_reminders=result.due,
    )
