"""Le fil d'une fiche (SPEC 6.1, D139) : un changement de statut ou une note, daté. Le statut ne
change que par ici (jamais par `PATCH`). Un changement de statut pose les dates de `on_status`
(7.1) ; le passage à « Postulée » fige la version de CV envoyée. Sous le verrou des
candidatures. Journaux : identifiants et statuts seulement, jamais une note."""

import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_moment, local_today
from app.db.models.applications import Application
from app.features.applications.repository import EventRepository
from app.features.applications.schemas import ApplicationDetail, EventIn
from app.features.applications.service.adopt import freeze_version
from app.features.applications.service.rules import on_status
from app.features.applications.service.runtime import ApplicationsRuntime
from app.features.applications.service.views import detail_out, get_application, invalid, view_of
from app.features.postings.service.duplicates import zone_of

logger = logging.getLogger(__name__)


def event_moment(day: date, today: date, now: datetime, zone: ZoneInfo) -> datetime:
    """L'instant du fil : maintenant pour aujourd'hui, midi (heure de January) pour un autre
    jour, qui place l'événement à sa date sans heure inventée."""
    return now if day == today else local_moment(day, "12:00", zone)


async def change_status(
    db: AsyncSession,
    user_id: str,
    row: Application,
    body: EventIn,
    when: tuple[date, datetime, ZoneInfo],
) -> None:
    """Applique le nouveau statut : dates de `on_status`, jour d'entretien donné, version figée à
    « Postulée » (la première fois), événement `status`. Sans effet si le statut ne change pas."""
    assert body.status is not None
    day, at, zone = when
    old = row.status
    if body.status == old:
        return
    first_application = body.status == "applied" and row.applied_on is None
    effects = on_status(view_of(row, zone), body.status, day).fields()
    for name, value in effects.items():
        setattr(row, name, value)
    if body.status == "interview" and body.interview_on is not None:
        row.interview_on = body.interview_on
    row.status = body.status
    await EventRepository(db, user_id).add(
        application_id=row.id,
        kind="status",
        at=at,
        status_from=old,
        status_to=body.status,
        text=body.text,
    )
    if first_application:
        await freeze_version(db, user_id, row, at)
    logger.info(
        "Statut changé : utilisateur %s, fiche %s, %s vers %s", user_id, row.id, old, body.status
    )


async def add_event(
    rt: ApplicationsRuntime, user_id: str, application_id: str, body: EventIn
) -> ApplicationDetail:
    """Ajoute l'événement au fil. 404 `application_not_found` ; 422 `status` (changement sans
    statut) ou `text` (note vide), sans écho."""
    if body.kind == "status" and body.status is None:
        raise invalid("status")
    if body.kind == "note" and not body.text:
        raise invalid("text")
    async with rt.lock(user_id), rt.session_factory() as db:
        row = await get_application(db, user_id, application_id)
        zone = await zone_of(db, user_id)
        now = rt.now()
        today = local_today(zone, now)
        day = body.on or today
        at = event_moment(day, today, now, zone)
        if body.kind == "status":
            await change_status(db, user_id, row, body, (day, at, zone))
        else:
            await EventRepository(db, user_id).add(
                application_id=row.id, kind="note", at=at, text=body.text
            )
        row.updated_at = now
        await db.commit()
        return await detail_out(db, user_id, row, today)
