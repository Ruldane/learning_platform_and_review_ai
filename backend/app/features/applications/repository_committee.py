"""Exécutions du comité de recrutement (D147). Chaque requête filtre par `user_id` ; les écritures
font un `flush`, le commit appartient à l'appelant."""

import builtins
from collections.abc import Collection

from sqlalchemy import literal_column, select

from app.db.models.applications import CommitteeRun
from app.db.repository import UserScopedRepository


class CommitteeRepository(UserScopedRepository[CommitteeRun]):
    model = CommitteeRun

    async def get_fresh(self, run_id: str) -> CommitteeRun | None:
        """L'exécution relue en base (jamais l'objet gardé par la session)."""
        stmt = (
            select(CommitteeRun)
            .where(CommitteeRun.id == run_id, CommitteeRun.user_id == self.user_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def recent(self, posting_id: str | None = None) -> builtins.list[CommitteeRun]:
        """Les exécutions (d'une offre), la plus récente d'abord."""
        stmt = select(CommitteeRun).where(CommitteeRun.user_id == self.user_id)
        if posting_id is not None:
            stmt = stmt.where(CommitteeRun.posting_id == posting_id)
        stmt = stmt.order_by(CommitteeRun.created_at.desc(), literal_column("rowid").desc())
        stmt = stmt.execution_options(populate_existing=True)
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def running(self, posting_id: str | None = None) -> builtins.list[CommitteeRun]:
        """Les exécutions en cours (d'une offre), la plus ancienne d'abord."""
        stmt = select(CommitteeRun).where(
            CommitteeRun.user_id == self.user_id, CommitteeRun.status == "running"
        )
        if posting_id is not None:
            stmt = stmt.where(CommitteeRun.posting_id == posting_id)
        stmt = stmt.order_by(CommitteeRun.created_at, literal_column("rowid"))
        stmt = stmt.execution_options(populate_existing=True)
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def last_done(self, posting_id: str) -> CommitteeRun | None:
        """La dernière exécution terminée de l'offre."""
        stmt = (
            select(CommitteeRun)
            .where(
                CommitteeRun.user_id == self.user_id,
                CommitteeRun.posting_id == posting_id,
                CommitteeRun.status == "done",
            )
            .order_by(CommitteeRun.created_at.desc(), literal_column("rowid").desc())
            .limit(1)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def by_ids(self, run_ids: Collection[str]) -> dict[str, CommitteeRun]:
        if not run_ids:
            return {}
        stmt = select(CommitteeRun).where(
            CommitteeRun.user_id == self.user_id, CommitteeRun.id.in_(builtins.list(run_ids))
        )
        return {row.id: row for row in (await self.session.execute(stmt)).scalars()}
