"""Mock interviews (D146). Every query filters by `user_id`; writes `flush`, the commit belongs
to the caller."""

import builtins

from sqlalchemy import literal_column, select

from app.db.models.applications import Interview
from app.db.repository import UserScopedRepository


class InterviewRepository(UserScopedRepository[Interview]):
    model = Interview

    async def get_fresh(self, interview_id: str) -> Interview | None:
        """The interview re-read from the database (never the object held by the session)."""
        stmt = (
            select(Interview)
            .where(Interview.id == interview_id, Interview.user_id == self.user_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def recent(self, application_id: str | None = None) -> builtins.list[Interview]:
        """The interviews (of a record), most recent first."""
        stmt = select(Interview).where(
            Interview.user_id == self.user_id, Interview.system_design.is_(None)
        )
        if application_id is not None:
            stmt = stmt.where(Interview.application_id == application_id)
        stmt = stmt.order_by(Interview.created_at.desc(), literal_column("rowid").desc())
        stmt = stmt.execution_options(populate_existing=True)
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def recent_design(self) -> Interview | None:
        stmt = (
            select(Interview)
            .where(Interview.user_id == self.user_id, Interview.system_design.is_not(None))
            .order_by(Interview.created_at.desc(), literal_column("rowid").desc())
            .limit(1)
        )
        return await self.session.scalar(stmt)

    async def running(self) -> builtins.list[Interview]:
        stmt = (
            select(Interview)
            .where(Interview.user_id == self.user_id, Interview.status == "running")
            .order_by(Interview.created_at, literal_column("rowid"))
            .execution_options(populate_existing=True)
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())
