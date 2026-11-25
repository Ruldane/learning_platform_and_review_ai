"""A user's briefs (13.6) and reads of already known links. Contended writes are guarded in
SQL (`INSERT … ON CONFLICT DO NOTHING`, `UPDATE … WHERE` on the expected state): two requests
or two jobs never create two briefs for one day, and the first write of a section wins. The
caller owns the commit."""

import builtins
from datetime import date, datetime
from typing import Any

from sqlalchemy import CursorResult, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.db.models.applications import Application
from app.db.models.daily import Brief
from app.db.models.postings import JobPosting
from app.db.repository import UserScopedRepository


def _changed(result: Any) -> bool:
    return isinstance(result, CursorResult) and result.rowcount == 1


class BriefRepository(UserScopedRepository[Brief]):
    model = Brief

    async def get_fresh(self, brief_id: str) -> Brief | None:
        stmt = (
            select(Brief)
            .where(Brief.id == brief_id, Brief.user_id == self.user_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def by_day(self, day: date) -> Brief | None:
        stmt = (
            select(Brief)
            .where(Brief.user_id == self.user_id, Brief.day == day)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def before(self, day: date, limit: int) -> builtins.list[Brief]:
        """Briefs of the days before `day`, most recent first."""
        stmt = (
            select(Brief)
            .where(Brief.user_id == self.user_id, Brief.day < day)
            .order_by(Brief.day.desc())
            .limit(limit)
        )
        return builtins.list((await self.session.execute(stmt)).scalars())

    async def insert_if_absent(
        self,
        *,
        day: date,
        origin: str,
        sections: dict[str, Any],
        offer_keys: builtins.list[str],
        now: datetime,
    ) -> str | None:
        """Create the brief for the day and return its id; `None` if that day already has its brief
        (nothing changes). Only the caller that receives an id launches the advice session."""
        stmt = (
            sqlite_insert(Brief)
            .values(
                user_id=self.user_id,
                day=day,
                origin=origin,
                sections=sections,
                offer_keys=offer_keys,
                advice_status="pending",
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_nothing(index_elements=["user_id", "day"])
            .returning(Brief.id)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _update_where(self, brief_id: str, *where: Any, **values: Any) -> bool:
        stmt = (
            update(Brief)
            .where(Brief.id == brief_id, Brief.user_id == self.user_id, *where)
            .values(**values)
        )
        return _changed(await self.session.execute(stmt))

    async def set_session(self, brief_id: str, session_id: str) -> bool:
        return await self._update_where(brief_id, Brief.session_id.is_(None), session_id=session_id)

    async def save_resource(self, brief_id: str, resource: dict[str, Any]) -> bool:
        """First write wins: `{}` is the empty section (stored, without a resource)."""
        return await self._update_where(brief_id, Brief.resource.is_(None), resource=resource)

    async def save_advice(self, brief_id: str, advice: dict[str, Any]) -> bool:
        return await self._update_where(
            brief_id,
            Brief.advice.is_(None),
            Brief.advice_status == "pending",
            advice=advice,
            advice_status="ready",
        )

    async def close_advice(self, brief_id: str, status: str) -> bool:
        """Advice `failed` or `unavailable`, only if still `pending`: final."""
        return await self._update_where(
            brief_id, Brief.advice_status == "pending", advice_status=status
        )

    async def known_keys(self) -> builtins.set[str]:
        """Normalised links of the postings and applications already entered."""
        keys: builtins.set[str] = set()
        for model in (JobPosting, Application):
            stmt = select(model.url_norm).where(
                model.user_id == self.user_id, model.url_norm.is_not(None)
            )
            keys.update(str(key) for key in (await self.session.execute(stmt)).scalars())
        return keys

    async def created_between(
        self, after: datetime | None, before: datetime | None, limit: int
    ) -> builtins.list[Brief]:
        """Briefs created within `[after, before]` (bounds included), most recent first (activity
        feed)."""
        stmt = select(Brief).where(Brief.user_id == self.user_id)
        if after is not None:
            stmt = stmt.where(Brief.created_at >= after)
        if before is not None:
            stmt = stmt.where(Brief.created_at <= before)
        stmt = stmt.order_by(Brief.created_at.desc(), Brief.id.desc()).limit(limit)
        return builtins.list((await self.session.execute(stmt)).scalars())
