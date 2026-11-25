"""Persistent ledger of scheduled runs (P13): one row per `(user_id, name, period)`.

Contested writes are guarded in SQL, so that two processes or two tasks never win the same run:
`INSERT … ON CONFLICT DO NOTHING`, then `UPDATE … WHERE` on the expected state (status, number
of attempts). The commit belongs to the caller. No read without `user_id` here: the accounts
that the scheduled tasks process come from the settings (D197)."""

from datetime import datetime
from typing import Any

from sqlalchemy import CursorResult, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.db.models.daily import JobRun
from app.db.repository import UserScopedRepository


def _changed(result: Any) -> bool:
    return isinstance(result, CursorResult) and result.rowcount == 1


class JobRunRepository(UserScopedRepository[JobRun]):
    model = JobRun

    async def insert_running(self, name: str, period: str, now: datetime) -> str | None:
        """Creates the `running` run (attempt 1) and returns its id; `None` if the period already
        has its row (nothing is changed)."""
        stmt = (
            sqlite_insert(JobRun)
            .values(
                user_id=self.user_id, name=name, period=period, status="running", started_at=now
            )
            .on_conflict_do_nothing(index_elements=["user_id", "name", "period"])
            .returning(JobRun.id)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def by_period(self, name: str, period: str) -> JobRun | None:
        stmt = (
            select(JobRun)
            .where(JobRun.user_id == self.user_id, JobRun.name == name, JobRun.period == period)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def reclaim(self, run_id: str, old_attempts: int, now: datetime) -> bool:
        """Resumes a `failed` or `running` run: next attempt, only if nobody has already resumed
        it (`attempts` unchanged) nor finished it."""
        stmt = (
            update(JobRun)
            .where(
                JobRun.id == run_id,
                JobRun.user_id == self.user_id,
                JobRun.attempts == old_attempts,
                JobRun.status.in_(("failed", "running")),
            )
            .values(
                status="running",
                started_at=now,
                finished_at=None,
                error_code=None,
                attempts=old_attempts + 1,
                updated_at=now,
            )
        )
        return _changed(await self.session.execute(stmt))

    async def close_running(self, run_id: str, attempt: int, now: datetime, **values: Any) -> bool:
        """Ends the `attempt` of a run still `running` (never a run already finished, nor another
        one, nor an attempt resumed since: a stale worker does not close the next attempt)."""
        stmt = (
            update(JobRun)
            .where(
                JobRun.id == run_id,
                JobRun.user_id == self.user_id,
                JobRun.status == "running",
                JobRun.attempts == attempt,
            )
            .values(finished_at=now, updated_at=now, **values)
        )
        return _changed(await self.session.execute(stmt))

    async def reopen_done(self, run_id: str, attempt: int, now: datetime, code: str) -> bool:
        """A `done` run whose launched work failed goes back to `failed` (attempt `attempt`
        only): `claim` can resume it, within the limit of attempts. `finished_at` moves to `now`:
        the activity feed dates the failure from its reopening, not from the launch."""
        stmt = (
            update(JobRun)
            .where(
                JobRun.id == run_id,
                JobRun.user_id == self.user_id,
                JobRun.status == "done",
                JobRun.attempts == attempt,
            )
            .values(status="failed", error_code=code, finished_at=now, updated_at=now)
        )
        return _changed(await self.session.execute(stmt))

    async def abandon(self, run_id: str, old_attempts: int, now: datetime) -> bool:
        """A stale `running` run with no attempt left goes to `failed` (`abandoned`), to appear in
        the feed instead of staying "in progress"."""
        stmt = (
            update(JobRun)
            .where(
                JobRun.id == run_id,
                JobRun.user_id == self.user_id,
                JobRun.attempts == old_attempts,
                JobRun.status == "running",
            )
            .values(status="failed", finished_at=now, error_code="abandoned", updated_at=now)
        )
        return _changed(await self.session.execute(stmt))

    async def last_done(self, name: str) -> JobRun | None:
        stmt = (
            select(JobRun)
            .where(
                JobRun.user_id == self.user_id,
                JobRun.name == name,
                JobRun.status == "done",
                JobRun.finished_at.is_not(None),
            )
            .order_by(JobRun.finished_at.desc(), JobRun.created_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def failures(
        self, after: datetime | None, before: datetime | None, limit: int
    ) -> list[JobRun]:
        """The failed runs finished within `[after, before]` (bounds included: the feed handles the
        ties itself), most recent first."""
        stmt = select(JobRun).where(JobRun.user_id == self.user_id, JobRun.status == "failed")
        if after is not None:
            stmt = stmt.where(JobRun.finished_at >= after)
        if before is not None:
            stmt = stmt.where(JobRun.finished_at <= before)
        stmt = stmt.order_by(JobRun.finished_at.desc(), JobRun.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars())
