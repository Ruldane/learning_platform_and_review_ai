"""Morning job (P12, P13, D162): called by the scheduled `daily_brief` job (`app.scheduler`, never
imported here: contract 8), every 10 minutes and at startup.

Per account, once the brief time has passed **for January** (`brief_due`, set time zone and
time): the run for the local day is won in the ledger (`claim`, period =
`day_period(brief_day(now, zone))`, never `now.date()`), then `ensure_today(origin="schedule")`.
The run closes `done` if it created the brief, `skipped` if the brief already existed (opened on
the home page before the time), with the brief id and tomorrow at the brief time; a failure marks
it `failed` (retried on the next run, 3 attempts at most). A failure for one account does not
stop the others. Logs: ids, numbers and codes."""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Literal

from app.core.clock import user_zone
from app.core.errors import AppError
from app.features.brief.service.ensure import ensure_today
from app.features.brief.service.rules import brief_day, brief_due
from app.features.brief.service.runtime import BriefRuntime
from app.features.ledger.service.ledger import Claim, claim, fail, finish, scheduled_user_ids
from app.features.ledger.service.periods import brief_moment, day_period
from app.features.settings.service import SettingsService

logger = logging.getLogger(__name__)

JOB = "daily_brief"


def _code(exc: Exception) -> str:
    return exc.code if isinstance(exc, AppError) else type(exc).__name__


@dataclass(frozen=True)
class Due:
    """An account that is due: the run won, the local day and the next run (tomorrow at the
    brief time)."""

    got: Claim
    today: date
    next_due_at: datetime


async def _claim_due(rt: BriefRuntime, user_id: str, now: datetime) -> Due | None:
    """The run won if this account is due: the brief time has passed and the local day is not
    already taken (not done, skipped, running, or out of attempts)."""
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
    logger.warning("Morning brief missed: user %s, %s", user_id, _code(exc))


async def _morning(rt: BriefRuntime, user_id: str, now: datetime) -> bool:
    """One account: return true if this run created the daily brief."""
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
    logger.info("Morning brief: user %s, brief %s, created %s", user_id, brief.id, created)
    return created


async def run_daily_briefs(rt: BriefRuntime, now: datetime) -> int:
    """One run of the scheduled job; return the number of briefs created."""
    async with rt.session_factory() as db:
        users = await scheduled_user_ids(db)
    created = 0
    for user_id in users:
        try:
            created += await _morning(rt, user_id, now)
        except Exception as exc:
            logger.warning("Morning brief: user %s not processed (%s)", user_id, type(exc).__name__)
    level = logging.INFO if created else logging.DEBUG
    logger.log(level, "Morning brief: %d account(s), %d brief(s)", len(users), created)
    return created
