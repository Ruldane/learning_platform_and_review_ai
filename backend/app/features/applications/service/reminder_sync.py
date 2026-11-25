"""Synchronising the expected reminders (SPEC 6.2, D140): what `expected_reminders` (7.1) says
about a record, compared with what is stored. An expected and missing reminder is created
"pending"; a pending reminder that is no longer expected (reply received, anchor changed,
record withdrawn) is deleted (never a done or ignored reminder: the deletion re-checks the
status); a done or ignored reminder is never touched (and never recreated: the anchor is
already there); a pending reminder that is still expected and not postponed takes the due date
given by the delays of the settings (same anchor); a reminder postponed by January
(`postponed`) keeps its own. Idempotent; creation ignores a `(record, type, anchor)` duplicate
(the database forbids it); reminder writes happen under the applications lock. Called on every
write that changes a record's status or dates, by `GET /reminders` and by the scheduled task.
Logs: ids and numbers only."""

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

_UTC = ZoneInfo("UTC")  # the record's creation date does not enter the due dates


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
    """A pending, non-postponed reminder takes the due date given by the delays (same
    anchor); returns 1 if it moved."""
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
    """Synchronises January's reminders (or those of a single record). `today`: January's day;
    the due dates do not depend on it (all expected reminders exist in advance), it serves the
    log. The commit belongs to the caller."""
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
    if removed:  # only pending reminders, even if another request has just closed one
        await db.execute(
            delete(Reminder).where(
                Reminder.user_id == user_id, Reminder.id.in_(removed), Reminder.status == "pending"
            )
        )
    if created or moved or removed:
        logger.info(
            "Reminders synchronised: user %s, day %s, %d created, %d moved, "
            "%d removed",
            user_id, today.isoformat(), created, moved, len(removed),
        )  # fmt: skip


async def sync_user(
    db: AsyncSession, user_id: str, today: date, *, application_id: str | None = None
) -> None:
    """`sync_reminders` with the delays of January's settings (3 waiting reminders)."""
    stored = await SettingsService(db, user_id).get()
    await sync_reminders(
        db, user_id, today, validated_delays(stored.reminder_delays_days),
        application_id=application_id,
    )  # fmt: skip
