"""Lectures des candidatures (SPEC 6.1, 6.4, D139) : liste (création décroissante), fiche
complète, indicateurs. La liste et les indicateurs adoptent d'abord les versions de CV prêtes
(`adopt`, SPEC 6.1 n° 1)."""

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
    """Le jour de January à l'instant `now` (son fuseau)."""
    return local_today(await zone_of(db, user_id), now)


async def list_applications(
    rt: ApplicationsRuntime,
    db: AsyncSession,
    user_id: str,
    *,
    status: str | None = None,
    posting_id: str | None = None,
) -> list[ApplicationOut]:
    """Les fiches, la plus récente d'abord ; adopte d'abord les versions prêtes."""
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
    """Fiches par statut, taux et délai moyen de réponse, relances dues (SPEC 6.4)."""
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
