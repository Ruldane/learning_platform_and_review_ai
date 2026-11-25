"""Radar scans of a user (13.5). Reads that precede a write refresh the row (`populate_existing`):
under a scan's lock, a query sees the state committed by the previous one. The commit belongs
to the caller."""

import builtins
from datetime import datetime

from sqlalchemy import select

from app.db.models.daily import RadarRun
from app.db.repository import UserScopedRepository


class RadarRunRepository(UserScopedRepository[RadarRun]):
    model = RadarRun

    async def get_fresh(self, run_id: str) -> RadarRun | None:
        stmt = (
            select(RadarRun)
            .where(RadarRun.id == run_id, RadarRun.user_id == self.user_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def running(self) -> builtins.list[RadarRun]:
        """The `running` scans, re-read."""
        stmt = (
            select(RadarRun)
            .where(RadarRun.user_id == self.user_id, RadarRun.status == "running")
            .order_by(RadarRun.created_at, RadarRun.id)
            .execution_options(populate_existing=True)
        )
        return builtins.list((await self.session.execute(stmt)).scalars())

    async def recent(self, limit: int) -> builtins.list[RadarRun]:
        stmt = (
            select(RadarRun)
            .where(RadarRun.user_id == self.user_id)
            .order_by(RadarRun.created_at.desc(), RadarRun.id.desc())
            .limit(limit)
            .execution_options(populate_existing=True)
        )
        return builtins.list((await self.session.execute(stmt)).scalars())

    async def latest_finished(self) -> RadarRun | None:
        """The most recent finished scan (`done` or `failed`)."""
        stmt = (
            select(RadarRun)
            .where(RadarRun.user_id == self.user_id, RadarRun.status != "running")
            .order_by(RadarRun.created_at.desc(), RadarRun.id.desc())
            .limit(1)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def latest_done(
        self,
        *,
        role_norm: str | None = None,
        zone_norm: str | None = None,
        before: datetime | None = None,
        exclude_id: str | None = None,
        min_analyzed: int = 0,
    ) -> RadarRun | None:
        """The last `done` scan, for this job and this area (normalized) if given, created before
        `before` if given, with at least `min_analyzed` offers analysed: a "blind" scan (no offer
        analysed) is never a reference."""
        stmt = select(RadarRun).where(RadarRun.user_id == self.user_id, RadarRun.status == "done")
        if role_norm is not None:
            stmt = stmt.where(RadarRun.role_norm == role_norm)
        if zone_norm is not None:
            stmt = stmt.where(RadarRun.zone_norm == zone_norm)
        if before is not None:
            stmt = stmt.where(RadarRun.created_at < before)
        if exclude_id is not None:
            stmt = stmt.where(RadarRun.id != exclude_id)
        if min_analyzed > 0:
            stmt = stmt.where(RadarRun.analyzed >= min_analyzed)
        stmt = stmt.order_by(RadarRun.created_at.desc(), RadarRun.id.desc()).limit(1)
        return (
            await self.session.execute(stmt.execution_options(populate_existing=True))
        ).scalar_one_or_none()

    async def created_since(self, since: datetime) -> bool:
        """Has a scan that did not fail (running or finished) been created since `since`? A failed
        scan does not hold the week: the scheduled run may replace it."""
        stmt = (
            select(RadarRun.id)
            .where(
                RadarRun.user_id == self.user_id,
                RadarRun.created_at >= since,
                RadarRun.status != "failed",
            )
            .limit(1)
        )
        return (await self.session.execute(stmt)).first() is not None

    async def done_since(self, since: datetime) -> builtins.list[RadarRun]:
        """The `done` scans finished after `since`, most recent first."""
        stmt = (
            select(RadarRun)
            .where(
                RadarRun.user_id == self.user_id,
                RadarRun.status == "done",
                RadarRun.finished_at > since,
            )
            .order_by(RadarRun.finished_at.desc(), RadarRun.id.desc())
            .execution_options(populate_existing=True)
        )
        return builtins.list((await self.session.execute(stmt)).scalars())

    async def done_between(
        self, after: datetime | None, before: datetime | None, limit: int | None
    ) -> builtins.list[RadarRun]:
        """The `done` scans finished within `[after, before]` (bounds included), most recent first
        (activity feed)."""
        stmt = select(RadarRun).where(
            RadarRun.user_id == self.user_id,
            RadarRun.status == "done",
            RadarRun.finished_at.is_not(None),
        )
        if after is not None:
            stmt = stmt.where(RadarRun.finished_at >= after)
        if before is not None:
            stmt = stmt.where(RadarRun.finished_at <= before)
        stmt = stmt.order_by(RadarRun.finished_at.desc(), RadarRun.id.desc()).limit(limit)
        return builtins.list((await self.session.execute(stmt)).scalars())
