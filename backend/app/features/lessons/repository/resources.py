import builtins
from dataclasses import dataclass

from sqlalchemy import literal_column, select

from app.db.models.lessons import Resource
from app.db.repository import UserScopedRepository


@dataclass(frozen=True)
class ResourceFilter:
    """Filtres de la Bibliothèque (SPEC 3.6) ; `None` : pas de filtre."""

    program_id: str | None = None
    type: str | None = None
    lang: str | None = None
    status: str | None = None


class ResourceRepository(UserScopedRepository[Resource]):
    model = Resource

    async def for_module(self, module_id: str) -> builtins.list[Resource]:
        stmt = (
            select(Resource)
            .where(Resource.user_id == self.user_id, Resource.module_id == module_id)
            .order_by(Resource.created_at, literal_column("rowid"))
            .execution_options(populate_existing=True)
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def by_url(self, module_id: str, url_hash: str) -> Resource | None:
        stmt = select(Resource).where(
            Resource.user_id == self.user_id,
            Resource.module_id == module_id,
            Resource.url_hash == url_hash,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def filtered(self, f: ResourceFilter) -> builtins.list[Resource]:
        stmt = select(Resource).where(Resource.user_id == self.user_id)
        if f.program_id is not None:
            stmt = stmt.where(Resource.program_id == f.program_id)
        if f.type is not None:
            stmt = stmt.where(Resource.type == f.type)
        if f.lang is not None:
            stmt = stmt.where(Resource.lang == f.lang)
        if f.status is not None:
            stmt = stmt.where(Resource.status == f.status)
        stmt = stmt.order_by(Resource.created_at.desc(), literal_column("rowid").desc())
        return builtins.list((await self.session.execute(stmt)).scalars().all())
