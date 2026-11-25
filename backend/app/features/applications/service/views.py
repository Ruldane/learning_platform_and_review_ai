"""Les fiches vues par le service et par les routes (D139) : `ApplicationView` pour les règles
(doublons, indicateurs, 7.1), `ApplicationOut` et `ApplicationDetail` pour l'API, `AlertOut` pour
l'alerte doublon. Les jours se comptent dans le fuseau de January."""

from collections.abc import Iterable, Sequence
from datetime import date
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.applications import Application, ApplicationEvent, Contact
from app.features.applications.repository import (
    ApplicationRepository,
    ContactRepository,
    EventRepository,
)
from app.features.applications.schemas import (
    AlertOut,
    ApplicationDetail,
    ApplicationOut,
    ContactOut,
    EventOut,
)
from app.features.applications.service.matching import Hit, alert_message
from app.features.applications.service.reminders_out import reminder_outs
from app.features.applications.service.rules import ApplicationView
from app.features.cv.service.versions import version_numbers

_OUT_FIELDS = (
    "id",
    "posting_id",
    "company",
    "title",
    "url",
    "channel",
    "status",
    "applied_on",
    "interview_on",
    "cv_version_id",
    "next_action",
    "next_action_on",
    "created_at",
    "updated_at",
)


def not_found() -> AppError:
    return AppError("application_not_found", "Application not found.", 404)


def invalid(*fields: str) -> AppError:
    """Une 422 qui nomme les champs, sans jamais citer leur valeur."""
    return AppError(
        "validation_error",
        "Invalid request. Check the highlighted fields.",
        422,
        {"fields": list(fields)},
    )


def created_on(row: Application, zone: ZoneInfo) -> date:
    return row.created_at.astimezone(zone).date()


def view_of(row: Application, zone: ZoneInfo) -> ApplicationView:
    return ApplicationView(
        id=row.id,
        status=row.status,  # type: ignore[arg-type]  # la colonne est un texte, les valeurs sont ApplicationStatus
        company_norm=row.company_norm,
        title=row.title,
        url_norm=row.url_norm,
        posting_id=row.posting_id,
        applied_on=row.applied_on,
        interview_on=row.interview_on,
        answered_on=row.answered_on,
        created_on=created_on(row, zone),
        distinct_from=frozenset(str(item) for item in row.distinct_from),
    )


async def views_of(
    db: AsyncSession, user_id: str, zone: ZoneInfo, rows: Sequence[Application] | None = None
) -> list[ApplicationView]:
    """Les fiches de January pour les règles (doublons, indicateurs)."""
    found = rows if rows is not None else await ApplicationRepository(db, user_id).recent()
    return [view_of(row, zone) for row in found]


def alert_out(row: Application, level: str, zone: ZoneInfo, today: date) -> AlertOut:
    """L'alerte d'une fiche existante, avec son message (date de candidature ou de création, et
    statut)."""
    created = created_on(row, zone)
    return AlertOut.model_validate(
        {
            "level": level,
            "application_id": row.id,
            "company": row.company,
            "title": row.title,
            "status": row.status,
            "applied_on": row.applied_on,
            "created_on": created,
            "message": alert_message(
                level,  # type: ignore[arg-type]
                row.company,
                row.title,
                row.status,  # type: ignore[arg-type]
                row.applied_on or created,
                today,
            ),
        }
    )


async def alerts_out(
    db: AsyncSession, user_id: str, hits: Iterable[Hit], zone: ZoneInfo, today: date
) -> list[AlertOut]:
    """Les alertes des fiches trouvées, dans l'ordre des `hits`."""
    found = list(hits)
    rows = await ApplicationRepository(db, user_id).by_ids([hit.application_id for hit in found])
    return [alert_out(rows[hit.application_id], hit.level, zone, today) for hit in found]


def _application_out(row: Application, number: int | None, due: int) -> ApplicationOut:
    values = {name: getattr(row, name) for name in _OUT_FIELDS}
    return ApplicationOut.model_validate(
        {**values, "cv_version_number": number, "due_reminders": due}
    )


async def application_outs(
    db: AsyncSession, user_id: str, rows: Sequence[Application], today: date
) -> list[ApplicationOut]:
    """Les fiches pour l'API : numéro de la version de CV et relances dues, lus en une fois."""
    numbers = await version_numbers(db, user_id, {r.cv_version_id for r in rows if r.cv_version_id})
    due = await ApplicationRepository(db, user_id).due_counts(today)
    return [
        _application_out(row, numbers.get(row.cv_version_id or ""), due.get(row.id, 0))
        for row in rows
    ]


def _contact_out(row: Contact) -> ContactOut:
    return ContactOut(id=row.id, name=row.name, role=row.role, url=row.url)


def _event_out(row: ApplicationEvent) -> EventOut:
    return EventOut.model_validate(
        {
            "id": row.id,
            "kind": row.kind,
            "at": row.at,
            "status_from": row.status_from,
            "status_to": row.status_to,
            "text": row.text,
            "ref_id": row.ref_id,
        }
    )


async def detail_out(
    db: AsyncSession, user_id: str, row: Application, today: date
) -> ApplicationDetail:
    """La fiche complète : contacts, fil chronologique et relances."""
    [base] = await application_outs(db, user_id, [row], today)
    contacts = await ContactRepository(db, user_id).of_application(row.id)
    events = await EventRepository(db, user_id).of_application(row.id)
    reminders = await ApplicationRepository(db, user_id).reminders(row.id)
    return ApplicationDetail(
        **base.model_dump(),
        posting_text=row.posting_text,
        letter=row.letter,
        notes=row.notes,
        contacts=[_contact_out(c) for c in contacts],
        events=[_event_out(e) for e in events],
        reminders=await reminder_outs(db, user_id, reminders),
    )


async def get_application(db: AsyncSession, user_id: str, application_id: str) -> Application:
    """La fiche de January, relue ; 404 `application_not_found` sinon."""
    row = await ApplicationRepository(db, user_id).get_fresh(application_id)
    if row is None:
        raise not_found()
    return row
