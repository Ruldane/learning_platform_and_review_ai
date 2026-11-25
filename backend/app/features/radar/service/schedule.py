"""Weekly radar run (P10, P13, D160): called by the scheduled task `market_radar`
(`app.scheduler`, never imported here: contract 8), every 15 minutes and at startup.

Per account, any day of the local ISO week from Monday 06:00 **local** (the catch-up: a missed
or failed Monday is retried on Tuesday, 3 tries at most): the week's pass is won in the
registry (`claim`, period = `week_period(local_today(zone, now))`, never `now.date()`: Sunday
23:30 in New York is already Monday UTC) and stays unique per week. A run created this week
(manual included, except a failed run) or no role: `skipped` pass. Otherwise the run starts
(`trigger="schedule"`) and the pass is `done` with the run's id and the following Monday; if
that run then fails, the pass is reopened and retried (3 tries at most). A failure for one
account does not stop the others. Logs: ids, numbers and codes."""

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
    scheduled_user_ids,
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
    """A due account: the pass won, the period (local ISO week) and the start of that local
    week (UTC instant)."""

    got: Claim
    period: str
    week_begins: datetime


async def _claim_due(rt: RadarRuntime, user_id: str, now: datetime) -> Due | None:
    """The pass won if this account is due: Monday 06:00 local of the current week has passed
    (any day of the week), the week's period not yet taken."""
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
    """This week's `done` pass whose launched run failed (dead session, Analyst failure) counts
    as not done: it goes back to `failed` and `claim` takes it over, within the limit of 3
    tries (like `ats_refresh`)."""
    async with rt.runs_lock(user_id):
        await settle(db, user_id, rt.now())
        last = await last_done(db, user_id, JOB)
        if last is None or last.period != period or last.ref_id is None:
            return
        run = await RadarRunRepository(db, user_id).get_fresh(last.ref_id)
        # Cancelled by January herself: never relaunched (like `ats_refresh`, which only reopens
        # on a `failed` session).
        if run is not None and run.status == "failed" and run.error_code != SESSION_CANCELLED:
            await reopen(db, user_id, last, code=run.error_code or RUN_FAILED, now=now)
            await db.commit()


async def _week_taken(rt: RadarRuntime, user_id: str, week_begins: datetime) -> bool:
    """A non-failed run (manual included) has already been created this week, or there is no
    role to run: the pass is skipped. First corrects a run whose session is dead."""
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
            logger.info("Weekly run skipped: user %s", user_id)
            return False
        started = await start_run(rt, user_id, RadarRunIn(), trigger="schedule", period=due.period)
    except AppError as exc:
        if exc.code in _SKIP_CODES:
            await _close(rt, user_id, due.got, now, "skipped")
            logger.info("Weekly run skipped: user %s, %s", user_id, exc.code)
        else:
            await _fail(rt, user_id, due.got, now, exc)
        return False
    except Exception as exc:
        await _fail(rt, user_id, due.got, now, exc)
        return False
    next_due = await _next_monday(rt, user_id, now)
    await _close(rt, user_id, due.got, now, "done", started.run_id, next_due)
    logger.info("Weekly run started: user %s, run %s", user_id, started.run_id)
    return True


async def _fail(rt: RadarRuntime, user_id: str, got: Claim, now: datetime, exc: Exception) -> None:
    async with rt.session_factory() as db:
        await fail(db, user_id, got.run_id, attempt=got.attempt, code=_code(exc), now=now)
        await db.commit()
    logger.warning("Weekly run missed: user %s, %s", user_id, _code(exc))


async def run_weekly_radar(rt: RadarRuntime, now: datetime) -> int:
    """One pass of the scheduled task; returns the number of runs started."""
    async with rt.session_factory() as db:
        users = await scheduled_user_ids(db)
    launched = 0
    for user_id in users:
        try:
            launched += await _weekly(rt, user_id, now)
        except Exception as exc:
            logger.warning("Weekly run: user %s not processed (%s)", user_id, type(exc).__name__)
    level = logging.INFO if launched else logging.DEBUG
    logger.log(level, "Weekly run: %d account(s), %d run(s)", len(users), launched)
    return launched
