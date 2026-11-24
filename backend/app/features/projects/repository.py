"""A user's mini projects (13.3). Reads that precede a write refresh the row
(`populate_existing`): under a project's lock, a request sees the state committed by the
previous one. Creation is guarded in SQL (`INSERT … ON CONFLICT DO NOTHING` on
`(user_id, module_id)`): two passes never create two projects for one module. The commit
belongs to the caller."""

import builtins
from collections.abc import Collection
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.db.models.daily import Project
from app.db.repository import UserScopedRepository


class ProjectRepository(UserScopedRepository[Project]):
    model = Project

    async def get_fresh(self, project_id: str) -> Project | None:
        stmt = (
            select(Project)
            .where(Project.id == project_id, Project.user_id == self.user_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def all(self, status: str | None = None) -> builtins.list[Project]:
        """The user's projects (those with this status if given), oldest first."""
        stmt = select(Project).where(Project.user_id == self.user_id)
        if status is not None:
            stmt = stmt.where(Project.status == status)
        stmt = stmt.order_by(Project.created_at, Project.id).execution_options(
            populate_existing=True
        )
        return builtins.list((await self.session.execute(stmt)).scalars())

    async def in_status(self, statuses: Collection[str]) -> builtins.list[Project]:
        """The projects in one of these statuses, re-read."""
        stmt = (
            select(Project)
            .where(Project.user_id == self.user_id, Project.status.in_(list(statuses)))
            .order_by(Project.created_at, Project.id)
            .execution_options(populate_existing=True)
        )
        return builtins.list((await self.session.execute(stmt)).scalars())

    async def module_ids(self) -> builtins.set[str]:
        """The modules that already have their project."""
        stmt = select(Project.module_id).where(Project.user_id == self.user_id)
        return builtins.set((await self.session.execute(stmt)).scalars())

    async def insert_if_absent(
        self, *, module_id: str, program_id: str, title: str, now: datetime
    ) -> str | None:
        """Creates the module's project (`brief_pending`, first attempt) and returns its id; `None`
        if the module already has its project (nothing changes). Only the caller that receives an
        id starts the brief session."""
        stmt = (
            sqlite_insert(Project)
            .values(
                user_id=self.user_id,
                module_id=module_id,
                program_id=program_id,
                title=title[:200],
                status="brief_pending",
                brief_attempts=1,
                submissions=[],
                drafts={},
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_nothing(index_elements=["user_id", "module_id"])
            .returning(Project.id)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()
