"""Tâche du matin (P12, P13, D162) : appelée par la tâche planifiée `daily_brief` (`app.scheduler`,
jamais importé ici : contrat 8), toutes les 10 minutes et au démarrage.

Par compte, une fois l'heure du brief passée **chez January** (`brief_due`, fuseau et heure
réglés) : le passage du jour local se gagne dans le registre (`claim`, période =
`day_period(brief_day(now, zone))`, jamais `now.date()`), puis `ensure_today(origin="schedule")`.
Le passage se ferme `done` si ce passage a créé le brief, `skipped` s'il existait déjà (ouvert à
l'accueil avant l'heure), avec l'id du brief et demain à l'heure du brief ; une panne le met
`failed` (repris au passage suivant, 3 essais au plus). Une panne pour un compte n'arrête pas les
autres. Journaux : identifiants, nombres et codes."""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Literal

from app.core.clock import user_zone
from app.core.errors import AppError
from app.features.brief.service.ensure import ensure_today
from app.features.brief.service.rules import brief_day, brief_due
from app.features.brief.service.runtime import BriefRuntime
from app.features.ledger.service.ledger import Claim, claim, fail, finish, user_ids
from app.features.ledger.service.periods import brief_moment, day_period
from app.features.settings.service import SettingsService

logger = logging.getLogger(__name__)

JOB = "daily_brief"


def _code(exc: Exception) -> str:
    return exc.code if isinstance(exc, AppError) else type(exc).__name__


@dataclass(frozen=True)
class Due:
    """Un compte dû : le passage gagné, le jour local et le prochain passage (demain à l'heure du
    brief)."""

    got: Claim
    today: date
    next_due_at: datetime


async def _claim_due(rt: BriefRuntime, user_id: str, now: datetime) -> Due | None:
    """Le passage gagné si ce compte est dû : l'heure du brief est passée et le jour local n'est
    pas déjà pris (ni fait, ni sauté, ni en cours, ni sans essai restant)."""
    async with rt.session_factory() as db:
        settings = await SettingsService(db, user_id).get()
        zone = user_zone(settings.timezone)
        if not brief_due(now, zone, settings.brief_time):
            return None
        today = brief_day(now, zone)
        got = await claim(db, user_id, JOB, day_period(today), now)
        await db.commit()
    if got is None:
        return None
    return Due(got, today, brief_moment(today + timedelta(days=1), settings.brief_time, zone))


async def _close(
    rt: BriefRuntime,
    user_id: str,
    got: Claim,
    now: datetime,
    status: Literal["done", "skipped"],
    brief_id: str,
    next_due_at: datetime,
) -> None:
    async with rt.session_factory() as db:
        await finish(
            db,
            user_id,
            got.run_id,
            attempt=got.attempt,
            status=status,
            now=now,
            ref_id=brief_id,
            next_due_at=next_due_at,
        )
        await db.commit()


async def _fail(rt: BriefRuntime, user_id: str, got: Claim, now: datetime, exc: Exception) -> None:
    async with rt.session_factory() as db:
        await fail(db, user_id, got.run_id, attempt=got.attempt, code=_code(exc), now=now)
        await db.commit()
    logger.warning("Brief du matin manqué : utilisateur %s, %s", user_id, _code(exc))


async def _morning(rt: BriefRuntime, user_id: str, now: datetime) -> bool:
    """Un compte : rend vrai si ce passage a créé le brief du jour."""
    due = await _claim_due(rt, user_id, now)
    if due is None:
        return False
    try:
        brief, created = await ensure_today(rt, user_id, origin="schedule", now=now)
    except Exception as exc:
        await _fail(rt, user_id, due.got, now, exc)
        return False
    await _close(
        rt, user_id, due.got, now, "done" if created else "skipped", brief.id, due.next_due_at
    )
    logger.info("Brief du matin : utilisateur %s, brief %s, créé %s", user_id, brief.id, created)
    return created


async def run_daily_briefs(rt: BriefRuntime, now: datetime) -> int:
    """Un passage de la tâche planifiée ; rend le nombre de briefs créés."""
    async with rt.session_factory() as db:
        users = await user_ids(db)
    created = 0
    for user_id in users:
        try:
            created += await _morning(rt, user_id, now)
        except Exception as exc:
            logger.warning(
                "Brief du matin : utilisateur %s non traité (%s)", user_id, type(exc).__name__
            )
    level = logging.INFO if created else logging.DEBUG
    logger.log(level, "Brief du matin : %d compte(s), %d brief(s)", len(users), created)
    return created
