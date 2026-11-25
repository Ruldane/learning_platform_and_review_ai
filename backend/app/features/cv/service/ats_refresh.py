"""Refreshing the ATS base (P14, D158): called by the scheduled task `ats_refresh`
(`app.scheduler`, never imported here: contract 8).

Each account is due when no `done` pass finished less than 30 days ago. The pass is won in the
registry (`claim`, period = January's local day, D98); then a `web_research` session is
launched with a fixed query about how ATSs work (subject `ats_refresh`). The ATS Reader then
re-reads its retained sources (`review_store.ats_updates`). A refused launch is stored under
its code (error type or `AppError` code, never the message) and retried on the next pass, 3
tries per day. A failure for one account does not stop the others. Logs: ids, numbers and codes
only."""

import logging
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.launcher import SessionLauncher
from app.core.clock import local_today, user_zone
from app.core.errors import AppError
from app.features.ledger.service.ledger import (
    Claim,
    JobRunView,
    claim,
    fail,
    finish,
    last_done,
    reopen,
    scheduled_user_ids,
)
from app.features.ledger.service.periods import ATS_EVERY_DAYS, day_period
from app.features.sessions.service import session_facts
from app.features.settings.service import SettingsService

logger = logging.getLogger(__name__)

JOB = "ats_refresh"
GRAPH = "web_research"
SUBJECT = "ats_refresh"
ATS_QUERY = (
    "how applicant tracking systems ATS work recruiting Greenhouse Workday Lever Teamtailor updates"
)


def _code(exc: Exception) -> str:
    return exc.code if isinstance(exc, AppError) else type(exc).__name__


SESSION_FAILED = "session_failed"
_MAX_REOPENED = 5


async def _last_good_done(db: AsyncSession, user_id: str, now: datetime) -> JobRunView | None:
    """The last `done` pass whose session has not failed. A `done` pass is written at launch:
    if its session is then `failed`, it counts as not done (it goes back to `failed` in the
    registry: retried on the next pass, within the limit of tries)."""
    for _ in range(_MAX_REOPENED):
        last = await last_done(db, user_id, JOB)
        if last is None or last.ref_id is None:
            return last
        facts = await session_facts(db, user_id, last.ref_id)
        if facts is None or facts.status != "failed":
            return last
        await reopen(db, user_id, last, code=SESSION_FAILED, now=now)
        await db.commit()
    return None


async def _claim_due(db: AsyncSession, user_id: str, now: datetime) -> Claim | None:
    """The pass won if this account is due, otherwise `None` (already done less than 30 days
    ago, or period already taken)."""
    last = await _last_good_done(db, user_id, now)
    finished = last.finished_at if last is not None else None
    if finished is not None and now - finished < timedelta(days=ATS_EVERY_DAYS):
        return None
    zone = user_zone((await SettingsService(db, user_id).get()).timezone)
    got = await claim(db, user_id, JOB, day_period(local_today(zone, now)), now)
    await db.commit()
    return got


async def _refresh(
    session_factory: async_sessionmaker[AsyncSession],
    launcher: SessionLauncher,
    user_id: str,
    now: datetime,
) -> bool:
    async with session_factory() as db:
        got = await _claim_due(db, user_id, now)
    if got is None:
        return False
    try:
        session_id = await launcher.start(
            user_id, GRAPH, {"query": ATS_QUERY}, subject_type=SUBJECT
        )
    except Exception as exc:
        async with session_factory() as db:
            await fail(db, user_id, got.run_id, attempt=got.attempt, code=_code(exc), now=now)
            await db.commit()
        logger.warning("ATS refresh: user %s, launch refused", user_id)
        return False
    async with session_factory() as db:
        await finish(
            db,
            user_id,
            got.run_id,
            attempt=got.attempt,
            status="done",
            now=now,
            ref_id=session_id,
            next_due_at=now + timedelta(days=ATS_EVERY_DAYS),
        )
        await db.commit()
    logger.info("ATS refresh: user %s, session %s", user_id, session_id)
    return True


async def run_ats_refresh(
    session_factory: async_sessionmaker[AsyncSession], launcher: SessionLauncher, now: datetime
) -> int:
    """One pass of the scheduled task; returns the number of sessions launched."""
    async with session_factory() as db:
        users = await scheduled_user_ids(db)
    launched = 0
    for user_id in users:
        try:
            launched += await _refresh(session_factory, launcher, user_id, now)
        except Exception as exc:
            logger.warning("ATS refresh: user %s not processed (%s)", user_id, type(exc).__name__)
    level = logging.INFO if launched else logging.DEBUG
    logger.log(level, "ATS refresh: %d account(s), %d session(s)", len(users), launched)
    return launched
