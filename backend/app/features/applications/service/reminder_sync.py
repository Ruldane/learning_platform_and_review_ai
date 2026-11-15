"""Synchronisation des relances attendues (SPEC 6.2, D140) : ce que `expected_reminders` (7.1) dit
d'une fiche, comparé à ce qui est enregistré. Une relance attendue et absente est créée « en
attente » ; une relance en attente qui n'est plus attendue (réponse reçue, ancre changée, fiche
retirée) est supprimée (jamais une relance faite ou ignorée : la suppression re-vérifie le
statut) ; une relance faite ou ignorée n'est jamais touchée (et n'est jamais recréée : l'ancre y
est déjà) ; une relance en attente encore attendue, non reportée, prend l'échéance que donnent les
délais des réglages (même ancre) ; une relance reportée par January (`postponed`) garde la sienne.
Idempotente ; la création ignore un doublon `(fiche, type, ancre)` (la base l'interdit) ; les
écritures de relances se font sous le verrou des candidatures. Appelée à chaque écriture qui change
le statut ou les dates d'une fiche, par `GET /reminders` et par la tâche planifiée. Journaux :
identifiants et nombres seulement."""

import logging
from datetime import date
from zoneinfo import ZoneInfo

from sqlalchemy import delete
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import new_id, utcnow
from app.db.models.applications import Application, Reminder
from app.features.applications.repository import ApplicationRepository, ReminderRepository
from app.features.applications.service.schedule import (
    Expected,
    expected_reminders,
    validated_delays,
)
from app.features.applications.service.views import view_of
from app.features.settings.service import SettingsService

logger = logging.getLogger(__name__)

_UTC = ZoneInfo("UTC")  # la date de création de la fiche n'entre pas dans les échéances


def _expected_of(
    row: Application, delays: tuple[int, int, int]
) -> dict[tuple[str, date], Expected]:
    return {(e.kind, e.anchor_on): e for e in expected_reminders(view_of(row, _UTC), delays)}


async def _create(db: AsyncSession, user_id: str, application_id: str, e: Expected) -> None:
    now = utcnow()
    await db.execute(
        insert(Reminder)
        .values(
            id=new_id(),
            user_id=user_id,
            application_id=application_id,
            kind=e.kind,
            anchor_on=e.anchor_on,
            due_on=e.due_on,
            status="pending",
            created_at=now,
            updated_at=now,
        )  # fmt: skip
        .on_conflict_do_nothing(index_elements=["application_id", "kind", "anchor_on"])
    )


def _follow_delays(current: Reminder, item: Expected) -> int:
    """Une relance en attente, non reportée, prend l'échéance que donnent les délais (même
    ancre) ; rend 1 si elle a bougé."""
    if current.status != "pending" or current.postponed or current.due_on == item.due_on:
        return 0
    current.due_on = item.due_on
    current.updated_at = utcnow()
    return 1


async def sync_reminders(
    db: AsyncSession,
    user_id: str,
    today: date,
    delays: tuple[int, int, int],
    *,
    application_id: str | None = None,
) -> None:
    """Synchronise les relances de January (ou d'une seule fiche). `today` : le jour de January ;
    les échéances n'en dépendent pas (toutes les relances attendues existent d'avance), il sert
    au journal. Le commit appartient à l'appelant."""
    repo = ApplicationRepository(db, user_id)
    if application_id is None:
        rows = await repo.recent()
    else:
        found = await repo.get(application_id)
        rows = [found] if found is not None else []
    stored: dict[str, dict[tuple[str, date], Reminder]] = {row.id: {} for row in rows}
    for reminder in await ReminderRepository(db, user_id).of_applications(list(stored)):
        stored[reminder.application_id][(reminder.kind, reminder.anchor_on)] = reminder
    created, moved, removed = 0, 0, []
    for row in rows:
        expected = _expected_of(row, delays)
        have = stored[row.id]
        removed += [
            r.id for key, r in have.items() if r.status == "pending" and key not in expected
        ]
        for key, item in expected.items():
            current = have.get(key)
            if current is None:
                await _create(db, user_id, row.id, item)
                created += 1
            else:
                moved += _follow_delays(current, item)
    if removed:  # seulement des relances en attente, même si une autre requête vient d'en clore une
        await db.execute(
            delete(Reminder).where(
                Reminder.user_id == user_id, Reminder.id.in_(removed), Reminder.status == "pending"
            )
        )
    if created or moved or removed:
        logger.info(
            "Relances synchronisées : utilisateur %s, jour %s, %d créée(s), %d déplacée(s), "
            "%d retirée(s)",
            user_id, today.isoformat(), created, moved, len(removed),
        )  # fmt: skip


async def sync_user(
    db: AsyncSession, user_id: str, today: date, *, application_id: str | None = None
) -> None:
    """`sync_reminders` avec les délais des réglages de January (3 relances d'attente)."""
    stored = await SettingsService(db, user_id).get()
    await sync_reminders(
        db, user_id, today, validated_delays(stored.reminder_delays_days),
        application_id=application_id,
    )  # fmt: skip
