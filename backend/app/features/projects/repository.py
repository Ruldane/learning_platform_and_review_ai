"""Mini projets d'un utilisateur (13.3). Les lectures qui précèdent une écriture rafraîchissent la
ligne (`populate_existing`) : sous le verrou d'un projet, une requête voit l'état commité par la
précédente. La création est gardée en SQL (`INSERT … ON CONFLICT DO NOTHING` sur
`(user_id, module_id)`) : deux passages ne créent jamais deux projets pour un module. Le commit
appartient à l'appelant."""

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
        """Les projets de l'utilisatrice (ceux de ce statut si donné), les plus anciens d'abord."""
        stmt = select(Project).where(Project.user_id == self.user_id)
        if status is not None:
            stmt = stmt.where(Project.status == status)
        stmt = stmt.order_by(Project.created_at, Project.id).execution_options(
            populate_existing=True
        )
        return builtins.list((await self.session.execute(stmt)).scalars())

    async def in_status(self, statuses: Collection[str]) -> builtins.list[Project]:
        """Les projets dans l'un de ces statuts, relus."""
        stmt = (
            select(Project)
            .where(Project.user_id == self.user_id, Project.status.in_(list(statuses)))
            .order_by(Project.created_at, Project.id)
            .execution_options(populate_existing=True)
        )
        return builtins.list((await self.session.execute(stmt)).scalars())

    async def module_ids(self) -> builtins.set[str]:
        """Les modules qui ont déjà leur projet."""
        stmt = select(Project.module_id).where(Project.user_id == self.user_id)
        return builtins.set((await self.session.execute(stmt)).scalars())

    async def insert_if_absent(
        self, *, module_id: str, program_id: str, title: str, now: datetime
    ) -> str | None:
        """Crée le projet du module (`brief_pending`, premier essai) et rend son id ; `None` si le
        module a déjà son projet (rien n'est changé). Seul celui qui reçoit un id lance la
        session de l'énoncé."""
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
