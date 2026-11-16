"""Relevé hebdomadaire du radar (P10, P13, D160) : appelé par la tâche planifiée `market_radar`
(`app.scheduler`, jamais importé ici : contrat 8), toutes les 15 minutes et au démarrage.

Par compte, un jour quelconque de la semaine ISO locale à partir du lundi 06:00 **locales** (le
rattrapage : un lundi manqué ou en échec est repris le mardi, 3 essais au plus) : le passage de la
semaine se gagne dans le registre (`claim`, période = `week_period(local_today(zone, now))`,
jamais `now.date()` : dimanche 23 h 30 à New York est déjà lundi UTC) et reste unique par
semaine. Un relevé créé cette semaine (manuel compris,
sauf un relevé en échec) ou aucun poste : passage `skipped`. Sinon le relevé part
(`trigger="schedule"`) et le passage est `done` avec l'id du relevé et le lundi suivant ; si ce
relevé échoue ensuite, le passage est rouvert et repris (3 essais au plus). Une panne
pour un compte n'arrête pas les autres. Journaux : identifiants, nombres et codes."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_moment, local_today, user_zone, week_start
from app.core.errors import AppError
from app.features.ledger.service.ledger import (
    Claim,
    claim,
    fail,
    finish,
    last_done,
    reopen,
    user_ids,
)
from app.features.ledger.service.periods import RADAR_TIME, week_period
from app.features.radar.repository import RadarRunRepository
from app.features.radar.schemas import RadarRunIn
from app.features.radar.service.runs import SESSION_CANCELLED, defaults, settle, start_run
from app.features.radar.service.runtime import RadarRuntime
from app.features.settings.service import SettingsService

logger = logging.getLogger(__name__)

JOB = "market_radar"
RUN_FAILED = "run_failed"
_SKIP_CODES = frozenset({"radar_in_progress", "radar_role_required"})


def _code(exc: Exception) -> str:
    return exc.code if isinstance(exc, AppError) else type(exc).__name__


@dataclass(frozen=True)
class Due:
    """Un compte dû : le passage gagné, la période (semaine ISO locale) et le début de cette
    semaine locale (instant UTC)."""

    got: Claim
    period: str
    week_begins: datetime


async def _claim_due(rt: RadarRuntime, user_id: str, now: datetime) -> Due | None:
    """Le passage gagné si ce compte est dû : le lundi 06:00 locales de la semaine en cours est
    passé (n'importe quel jour de la semaine), période de la semaine pas encore prise."""
    async with rt.session_factory() as db:
        zone = user_zone((await SettingsService(db, user_id).get()).timezone)
        today = local_today(zone, now)
        if now < local_moment(week_start(today), RADAR_TIME, zone):
            return None
        period = week_period(today)
        await _reopen_if_run_failed(rt, db, user_id, period, now)
        got = await claim(db, user_id, JOB, period, now)
        await db.commit()
    if got is None:
        return None
    return Due(got, period, local_moment(week_start(today), "00:00", zone))


async def _reopen_if_run_failed(
    rt: RadarRuntime, db: AsyncSession, user_id: str, period: str, now: datetime
) -> None:
    """Le passage `done` de cette semaine dont le relevé lancé a échoué (session morte, panne de
    l'Analyste) compte comme non fait : il repasse en `failed` et `claim` le reprend, dans la
    limite des 3 essais (comme `ats_refresh`)."""
    async with rt.runs_lock(user_id):
        await settle(db, user_id, rt.now())
        last = await last_done(db, user_id, JOB)
        if last is None or last.period != period or last.ref_id is None:
            return
        run = await RadarRunRepository(db, user_id).get_fresh(last.ref_id)
        # Annulé par January lui-même : jamais relancé (comme `ats_refresh`, qui ne rouvre que sur
        # une session `failed`).
        if run is not None and run.status == "failed" and run.error_code != SESSION_CANCELLED:
            await reopen(db, user_id, last, code=run.error_code or RUN_FAILED, now=now)
            await db.commit()


async def _week_taken(rt: RadarRuntime, user_id: str, week_begins: datetime) -> bool:
    """Un relevé non échoué (manuel compris) a déjà été créé cette semaine, ou il n'y a aucun
    poste à relever : le passage est sauté. Corrige d'abord un relevé dont la session est morte."""
    async with rt.runs_lock(user_id), rt.session_factory() as db:
        await settle(db, user_id, rt.now())
        if await RadarRunRepository(db, user_id).created_since(week_begins):
            return True
        return not (await defaults(db, user_id))[0]


async def _next_monday(rt: RadarRuntime, user_id: str, now: datetime) -> datetime:
    async with rt.session_factory() as db:
        zone = user_zone((await SettingsService(db, user_id).get()).timezone)
    monday = week_start(local_today(zone, now)) + timedelta(days=7)
    return local_moment(monday, RADAR_TIME, zone)


async def _close(
    rt: RadarRuntime,
    user_id: str,
    got: Claim,
    now: datetime,
    status: Literal["done", "skipped"],
    run_id: str | None = None,
    next_due_at: datetime | None = None,
) -> None:
    async with rt.session_factory() as db:
        await finish(
            db,
            user_id,
            got.run_id,
            attempt=got.attempt,
            status=status,
            now=now,
            ref_id=run_id,
            next_due_at=next_due_at,
        )
        await db.commit()


async def _weekly(rt: RadarRuntime, user_id: str, now: datetime) -> bool:
    due = await _claim_due(rt, user_id, now)
    if due is None:
        return False
    try:
        if await _week_taken(rt, user_id, due.week_begins):
            await _close(rt, user_id, due.got, now, "skipped")
            logger.info("Relevé hebdomadaire sauté : utilisateur %s", user_id)
            return False
        started = await start_run(rt, user_id, RadarRunIn(), trigger="schedule", period=due.period)
    except AppError as exc:
        if exc.code in _SKIP_CODES:
            await _close(rt, user_id, due.got, now, "skipped")
            logger.info("Relevé hebdomadaire sauté : utilisateur %s, %s", user_id, exc.code)
        else:
            await _fail(rt, user_id, due.got, now, exc)
        return False
    except Exception as exc:
        await _fail(rt, user_id, due.got, now, exc)
        return False
    next_due = await _next_monday(rt, user_id, now)
    await _close(rt, user_id, due.got, now, "done", started.run_id, next_due)
    logger.info("Relevé hebdomadaire lancé : utilisateur %s, relevé %s", user_id, started.run_id)
    return True


async def _fail(rt: RadarRuntime, user_id: str, got: Claim, now: datetime, exc: Exception) -> None:
    async with rt.session_factory() as db:
        await fail(db, user_id, got.run_id, attempt=got.attempt, code=_code(exc), now=now)
        await db.commit()
    logger.warning("Relevé hebdomadaire manqué : utilisateur %s, %s", user_id, _code(exc))


async def run_weekly_radar(rt: RadarRuntime, now: datetime) -> int:
    """Un passage de la tâche planifiée ; rend le nombre de relevés lancés."""
    async with rt.session_factory() as db:
        users = await user_ids(db)
    launched = 0
    for user_id in users:
        try:
            launched += await _weekly(rt, user_id, now)
        except Exception as exc:
            logger.warning(
                "Relevé hebdomadaire : utilisateur %s non traité (%s)", user_id, type(exc).__name__
            )
    level = logging.INFO if launched else logging.DEBUG
    logger.log(level, "Relevé hebdomadaire : %d compte(s), %d relevé(s)", len(users), launched)
    return launched
