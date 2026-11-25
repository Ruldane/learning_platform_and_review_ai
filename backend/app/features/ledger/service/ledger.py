"""Registry of scheduled passes (P13, D158): atomic `claim`, `finish`, `fail`, reads.

A pass is stored by `(user, task, period)` (`periods`). `claim` wins the period (insert without
conflict) or takes over a `failed` pass or a stale `running` one (30 minutes), 3 tries at most;
`done` and `skipped` are never taken over. The commit belongs to the caller: it commits right
after `claim`. Logs: ids, numbers and codes only."""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.daily import JobRun, JobStatus
from app.features.ledger.repository import JobRunRepository
from app.features.ledger.service.periods import MAX_ATTEMPTS, is_stale
from app.features.settings.service import scheduled_users

logger = logging.getLogger(__name__)

GENERIC_CODE = "error"
_CODE = re.compile(r"[A-Za-z0-9_.:-]{1,64}")


@dataclass(frozen=True)
class Claim:
    run_id: str
    attempt: int


@dataclass(frozen=True)
class JobRunView:
    run_id: str
    name: str
    period: str
    status: JobStatus
    started_at: datetime
    finished_at: datetime | None
    attempts: int
    error_code: str | None
    ref_id: str | None
    next_due_at: datetime | None


def _view(row: JobRun) -> JobRunView:
    return JobRunView(
        run_id=row.id,
        name=row.name,
        period=row.period,
        status=cast(JobStatus, row.status),
        started_at=row.started_at,
        finished_at=row.finished_at,
        attempts=row.attempts,
        error_code=row.error_code,
        ref_id=row.ref_id,
        next_due_at=row.next_due_at,
    )


def safe_code(code: str) -> str:
    """An error code (exception type or `AppError` code); any other text (a message may quote
    data) is replaced by `error`."""
    return code if _CODE.fullmatch(code) else GENERIC_CODE


async def claim(
    db: AsyncSession, user_id: str, name: str, period: str, now: datetime
) -> Claim | None:
    """Wins the pass `(name, period)` or returns `None` (already won, finished, running and not
    stale, or no try left). To be committed right away by the caller."""
    repo = JobRunRepository(db, user_id)
    created = await repo.insert_running(name, period, now)
    if created is not None:
        logger.debug("Registry: pass %s won (try 1)", created)
        return Claim(created, 1)
    row = await repo.by_period(name, period)
    if row is None or row.status in ("done", "skipped"):
        return None
    if row.status == "running" and not is_stale(row.started_at, now):
        return None
    run_id, old = row.id, row.attempts  # read before the UPDATE, which updates the session object
    if old >= MAX_ATTEMPTS:
        if row.status == "running" and await repo.abandon(run_id, old, now):
            logger.warning("Registry: pass %s abandoned after %d tries", run_id, old)
        return None
    if not await repo.reclaim(run_id, old, now):
        return None
    logger.info("Registry: pass %s taken over (try %d)", run_id, old + 1)
    return Claim(run_id, old + 1)


async def finish(
    db: AsyncSession,
    user_id: str,
    run_id: str,
    *,
    attempt: int,
    status: Literal["done", "skipped"],
    now: datetime,
    ref_id: str | None = None,
    next_due_at: datetime | None = None,
) -> None:
    """Ends the try `attempt` (the `Claim`'s): a stale worker, whose pass has been taken over
    since (next try), closes nothing."""
    done = await JobRunRepository(db, user_id).close_running(
        run_id, attempt, now, status=status, ref_id=ref_id, next_due_at=next_due_at, error_code=None
    )
    if done:
        logger.debug("Registry: pass %s finished (%s)", run_id, status)
    else:
        logger.info("Registry: pass %s, try %d already closed or taken over", run_id, attempt)


async def fail(
    db: AsyncSession, user_id: str, run_id: str, *, attempt: int, code: str, now: datetime
) -> None:
    """Fails the try `attempt` (see `finish`)."""
    code = safe_code(code)
    failed = await JobRunRepository(db, user_id).close_running(
        run_id, attempt, now, status="failed", error_code=code
    )
    if failed:
        logger.warning("Registry: pass %s failed (%s)", run_id, code)
    else:
        logger.info("Registry: pass %s, try %d already closed or taken over", run_id, attempt)


async def reopen(
    db: AsyncSession, user_id: str, view: JobRunView, *, code: str, now: datetime
) -> bool:
    """A `done` pass whose launched work failed goes back to `failed`: it counts as not done,
    `claim` takes it over (3 tries at most, like any failed pass)."""
    reopened = await JobRunRepository(db, user_id).reopen_done(
        view.run_id, view.attempts, now, safe_code(code)
    )
    if reopened:
        logger.warning("Registre : passage %s rouvert (%s)", view.run_id, safe_code(code))
    return reopened


async def last_done(db: AsyncSession, user_id: str, name: str) -> JobRunView | None:
    row = await JobRunRepository(db, user_id).last_done(name)
    return _view(row) if row is not None else None


async def recent_failures(
    db: AsyncSession, user_id: str, after: datetime | None, before: datetime | None, limit: int
) -> list[JobRunView]:
    """The failed passes finished in `[after, before]` (bounds included, most recent first),
    for the activity feed."""
    rows = await JobRunRepository(db, user_id).failures(after, before, limit)
    return [_view(row) for row in rows]


async def scheduled_user_ids(db: AsyncSession) -> list[str]:
    """The ONLY read without `user_id` of the registry's tasks (like D18, D91, D197): the
    accounts whose first launch is finished, the same rule as `GET /settings`
    (`onboarding_done`). An account that has not finished it takes no pass of the registry: it
    will be handled on the first pass that follows. Scheduled tasks that call a model or the web
    read no other."""
    return await scheduled_users(db)
