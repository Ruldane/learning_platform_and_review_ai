from typing import Any

from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.contributions import Contribution


class ContributionRepository:
    def __init__(self, db: AsyncSession, user_id: str) -> None:
        self._db = db
        self._user_id = user_id

    async def owned(self, contribution_id: str) -> Contribution:
        stmt = select(Contribution).where(
            Contribution.id == contribution_id, Contribution.user_id == self._user_id
        )
        row = (await self._db.scalars(stmt.execution_options(populate_existing=True))).one_or_none()
        if row is None:
            raise AppError("contribution_not_found", "Contribution dossier not found.", 404)
        return row

    async def list(self) -> list[Contribution]:
        stmt = (
            select(Contribution)
            .where(Contribution.user_id == self._user_id)
            .order_by(Contribution.updated_at.desc(), Contribution.id)
        )
        return list(await self._db.scalars(stmt))

    async def by_issue(self, repository: str, number: int) -> Contribution | None:
        stmt = select(Contribution).where(
            Contribution.user_id == self._user_id,
            Contribution.repository == repository,
            Contribution.issue_number == number,
        )
        return (
            await self._db.scalars(stmt.execution_options(populate_existing=True))
        ).one_or_none()

    async def make(self, **values: Any) -> Contribution:
        stmt = insert(Contribution).values(user_id=self._user_id, **values)
        stmt = stmt.on_conflict_do_nothing(index_elements=["user_id", "repository", "issue_number"])
        await self._db.execute(stmt)
        row = await self.by_issue(values["repository"], values["issue_number"])
        assert row is not None
        return row

    async def change(self, row: Contribution, **values: Any) -> bool:
        stmt = (
            update(Contribution)
            .where(
                Contribution.id == row.id,
                Contribution.user_id == self._user_id,
                Contribution.revision == row.revision,
            )
            .values(revision=Contribution.revision + 1, **values)
            .returning(Contribution.id)
        )
        return (await self._db.scalars(stmt)).one_or_none() is not None
