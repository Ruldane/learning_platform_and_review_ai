"""Les relances (SPEC 6.2, D140) : la liste (synchronisée d'abord), les trois actions de January
(Fait, Reporter de 3 jours, Ignorer) et le passage de la tâche planifiée. L'application n'envoie
jamais rien : le brouillon se copie. Sous le verrou des candidatures.

- `done` : relance faite, événement `reminder` ; la relance de 7 ou 14 jours d'une fiche
  « Postulée » la passe en « Relancée » ; la proposition de 21 jours la passe en « Sans réponse ».
- `postpone` : l'échéance devient le plus tardif de l'échéance et d'aujourd'hui, plus 3 jours ; la
  relance reste en attente.
- `ignore` : relance ignorée, événement `reminder`.
Une relance déjà faite ou ignorée : 409 `reminder_closed`. Journaux : identifiants et codes
seulement, jamais un brouillon, un contact, une entreprise ni un intitulé."""

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
    """Synchronise, puis rend les relances en attente dues aujourd'hui (`due`), ou toutes."""
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
    """Ce que « Fait » change au statut de la fiche."""
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
    """Applique l'action (voir le module). 404 `reminder_not_found` ; 409 `reminder_closed`."""
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
    """Un passage de la tâche planifiée, compte par compte : adopte les versions de CV (les
    fiches des offres prêtes), puis synchronise les relances. Une panne chez l'un n'arrête pas
    les autres."""
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
            logger.warning("Relances : utilisateur %s non traité (%s)", user_id, type(exc).__name__)
    level = logging.WARNING if failed else logging.DEBUG
    logger.log(level, "Relances : %d compte(s), %d en échec", len(users), failed)
