"""Reminders (SPEC 6.2, D140): the list (synchronised first), January's three actions
(Done, Postpone by 3 days, Ignore) and the scheduled task's pass. The application never sends
anything: the draft is copied. Under the applications lock.

- `done`: reminder done, `reminder` event; the 7 or 14-day reminder of an "Applied" record
  moves it to "Followed up"; the 21-day proposal moves it to "No response".
- `postpone`: the due date becomes the later of the due date and today, plus 3 days; the
  reminder stays pending.
- `ignore`: reminder ignored, `reminder` event.
An already done or ignored reminder: 409 `reminder_closed`. Logs: ids and codes only, never a
draft, a contact, a company or a title."""

import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_today
from app.core.errors import AppError
from app.db.models.applications import Application, ReminderKind
from app.features.applications.repository import EventRepository, ReminderRepository, user_ids
from app.features.applications.schemas import EventIn, ReminderActionName, ReminderOut
from app.features.applications.service.adopt import adopt
from app.features.applications.service.events import change_status
from app.features.applications.service.reminder_sync import sync_user
from app.features.applications.service.reminders_out import reminder_outs
from app.features.applications.service.rules import WAITING
from app.features.applications.service.runtime import ApplicationsRuntime
from app.features.applications.service.views import get_application
from app.features.postings.service.duplicates import zone_of

logger = logging.getLogger(__name__)

POSTPONE_DAYS = 3
LABELS: dict[ReminderKind, str] = {
    "linkedin_7": "LinkedIn follow-up",
    "email_14": "Email follow-up",
    "close_21": "No answer reminder",
    "thanks": "Interview thank-you",
    "news_7": "Interview follow-up",
}


def not_found() -> AppError:
    return AppError("reminder_not_found", "Reminder not found.", 404)


def closed() -> AppError:
    return AppError("reminder_closed", "This reminder was already completed or ignored.", 409)


async def list_reminders(rt: ApplicationsRuntime, user_id: str, *, due: bool) -> list[ReminderOut]:
    """Synchronises, then returns the pending reminders due today (`due`), or all of them."""
    async with rt.lock(user_id), rt.session_factory() as db:
        today = local_today(await zone_of(db, user_id), rt.now())
        await sync_user(db, user_id, today)
        await db.commit()
        rows = await ReminderRepository(db, user_id).listing(due_on=today if due else None)
        return await reminder_outs(db, user_id, rows)


async def _effect(
    db: AsyncSession,
    user_id: str,
    app: Application,
    kind: ReminderKind,
    when: tuple[date, datetime, ZoneInfo],
) -> None:
    """What "Done" changes in the record's status."""
    new: str | None = None
    if kind in ("linkedin_7", "email_14") and app.status == "applied":
        new = "followed_up"
    elif kind == "close_21" and app.status in WAITING:
        new = "no_answer"
    if new is not None:
        body = EventIn.model_validate({"kind": "status", "status": new})
        await change_status(db, user_id, app, body, when)
        app.updated_at = when[1]


async def act_on_reminder(
    rt: ApplicationsRuntime, user_id: str, reminder_id: str, action: ReminderActionName
) -> ReminderOut:
    """Applies the action (see the module). 404 `reminder_not_found`; 409 `reminder_closed`."""
    async with rt.lock(user_id), rt.session_factory() as db:
        row = await ReminderRepository(db, user_id).get_fresh(reminder_id)
        if row is None:
            raise not_found()
        if row.status != "pending":
            raise closed()
        app = await get_application(db, user_id, row.application_id)
        zone = await zone_of(db, user_id)
        now = rt.now()
        today = local_today(zone, now)
        if action == "postpone":
            row.due_on = max(row.due_on, today) + timedelta(days=POSTPONE_DAYS)
            row.postponed = True
        else:
            row.status = "done" if action == "done" else "ignored"
            if action == "done":
                row.done_at = now
            label = LABELS[row.kind]  # type: ignore[index]  # un texte, valeurs de ReminderKind
            outcome = "completed" if action == "done" else "ignored"
            await EventRepository(db, user_id).add(
                application_id=app.id,
                kind="reminder",
                at=now,
                text=f"{label} {outcome}.",
                ref_id=row.id,
            )
            if action == "done":
                await _effect(db, user_id, app, row.kind, (today, now, zone))  # type: ignore[arg-type]
        row.updated_at = now
        await sync_user(db, user_id, today, application_id=app.id)
        [out] = await reminder_outs(db, user_id, [row])
        await db.commit()
        logger.info("Relance %s : utilisateur %s, relance %s", action, user_id, reminder_id)
        return out


async def run_reminders(rt: ApplicationsRuntime, now: datetime) -> None:
    """One pass of the scheduled task, account by account: adopts the CV versions (the records
    of ready postings), then synchronises the reminders. A failure on one does not stop the
    others."""
    async with rt.session_factory() as db:
        users = await user_ids(db)
    failed = 0
    for user_id in users:
        try:
            await adopt(rt, user_id)
            async with rt.lock(user_id), rt.session_factory() as db:
                await sync_user(db, user_id, local_today(await zone_of(db, user_id), now))
                await db.commit()
        except Exception as exc:
            failed += 1
            logger.warning("Reminders: user %s not processed (%s)", user_id, type(exc).__name__)
    level = logging.WARNING if failed else logging.DEBUG
    logger.log(level, "Reminders: %d account(s), %d failed", len(users), failed)
