import builtins
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import ColumnElement, Select, exists, func, select, update
from sqlalchemy.orm.attributes import set_committed_value

from app.db.models.memory import ItemStatus, MemoryItem, MemoryKind
from app.db.repository import UserScopedRepository


@dataclass(frozen=True)
class ItemFilter:
    """Critères de la liste : `since` et `until` bornent `created_at` (inclusifs)."""

    kind: MemoryKind | None = None
    tag: str | None = None
    author: str | None = None
    since: datetime | None = None
    until: datetime | None = None
    status: ItemStatus = "active"


def _tag_condition(tag: str) -> ColumnElement[bool]:
    tags = func.json_each(MemoryItem.tags).table_valued("value")
    return exists().select_from(tags).where(tags.c.value == tag)


class MemoryItemRepository(UserScopedRepository[MemoryItem]):
    model = MemoryItem

    def _scoped(self, status: ItemStatus = "active") -> Select[MemoryItem]:
        return select(MemoryItem).where(
            MemoryItem.user_id == self.user_id, MemoryItem.status == status
        )

    async def begin_write(self) -> None:
        """Ouvre la transaction d'écriture avant un SAVEPOINT. pysqlite n'ouvre une transaction
        qu'à la première instruction d'écriture : sans elle, `begin_nested` en ouvrirait une et
        sa libération la validerait, hors de portée d'un `rollback` de la requête. La ligne visée
        n'existe pas ; si une transaction est déjà ouverte, c'est sans effet."""
        stmt = (
            update(MemoryItem).where(MemoryItem.id == "").values(updated_at=MemoryItem.updated_at)
        )
        await self.session.execute(stmt)

    async def set_indexed_at(self, item: MemoryItem, at: datetime | None) -> None:
        """Date d'indexation de `item` (`None` : à réindexer) ; `updated_at` n'est pas touché,
        indexer n'est pas modifier l'élément."""
        stmt = (
            update(MemoryItem)
            .where(MemoryItem.id == item.id, MemoryItem.user_id == self.user_id)
            .values(indexed_at=at, updated_at=MemoryItem.updated_at)
        )
        await self.session.execute(stmt)
        set_committed_value(item, "indexed_at", at)

    async def find_by_hash(self, content_hash: str) -> MemoryItem | None:
        stmt = select(MemoryItem).where(
            MemoryItem.user_id == self.user_id, MemoryItem.content_hash == content_hash
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def find_document_of(self, source_id: str) -> MemoryItem | None:
        """Élément `document` tiré du document `source_id` (le plus ancien s'il y en avait
        plusieurs)."""
        stmt = (
            select(MemoryItem)
            .where(
                MemoryItem.user_id == self.user_id,
                MemoryItem.kind == "document",
                MemoryItem.source_id == source_id,
            )
            .order_by(MemoryItem.created_at, MemoryItem.id)
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def filtered(
        self, f: ItemFilter, *, limit: int, offset: int
    ) -> tuple[builtins.list[MemoryItem], int]:
        """Éléments qui répondent à `f`, les plus récents d'abord, et leur nombre total
        (sans `limit` ni `offset`)."""
        stmt = self._scoped(f.status)
        conditions: builtins.list[ColumnElement[bool]] = []
        if f.kind is not None:
            conditions.append(MemoryItem.kind == f.kind)
        if f.tag is not None:
            conditions.append(_tag_condition(f.tag))
        if f.author is not None:
            conditions.append(MemoryItem.created_by == f.author)
        if f.since is not None:
            conditions.append(MemoryItem.created_at >= f.since)
        if f.until is not None:
            conditions.append(MemoryItem.created_at <= f.until)
        stmt = stmt.where(*conditions)
        total = (
            await self.session.execute(select(func.count()).select_from(stmt.subquery()))
        ).scalar_one()
        page = stmt.order_by(MemoryItem.created_at.desc(), MemoryItem.id.desc())
        rows = (await self.session.execute(page.limit(limit).offset(offset))).scalars().all()
        return builtins.list(rows), int(total)

    async def get_many(self, ids: Sequence[str]) -> dict[str, MemoryItem]:
        if not ids:
            return {}
        stmt = select(MemoryItem).where(
            MemoryItem.user_id == self.user_id, MemoryItem.id.in_(builtins.list(ids))
        )
        return {row.id: row for row in (await self.session.execute(stmt)).scalars()}

    async def count_by_kind(self, status: ItemStatus = "active") -> dict[str, int]:
        stmt = (
            select(MemoryItem.kind, func.count())
            .where(MemoryItem.user_id == self.user_id, MemoryItem.status == status)
            .group_by(MemoryItem.kind)
        )
        return {kind: int(n) for kind, n in (await self.session.execute(stmt)).all()}

    async def count_status(self, status: ItemStatus) -> int:
        stmt = select(func.count()).select_from(self._scoped(status).subquery())
        return int((await self.session.execute(stmt)).scalar_one())

    async def count_unindexed(self) -> int:
        """Éléments actifs pas encore indexés dans Qdrant."""
        stmt = select(func.count()).select_from(
            self._scoped().where(MemoryItem.indexed_at.is_(None)).subquery()
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def active(self, *, limit: int | None = None) -> builtins.list[MemoryItem]:
        stmt = self._scoped().order_by(MemoryItem.created_at.desc(), MemoryItem.id.desc())
        if limit is not None:
            stmt = stmt.limit(limit)
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def unindexed_batch(self, limit: int) -> builtins.list[MemoryItem]:
        """Éléments actifs à indexer, du plus ancien au plus récent."""
        stmt = (
            self._scoped()
            .where(MemoryItem.indexed_at.is_(None))
            .order_by(MemoryItem.created_at, MemoryItem.id)
            .limit(limit)
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def clear_indexed(self) -> None:
        """Marque tous les éléments actifs comme à réindexer (`updated_at` n'est pas touché)."""
        stmt = (
            update(MemoryItem)
            .where(MemoryItem.user_id == self.user_id, MemoryItem.status == "active")
            .values(indexed_at=None, updated_at=MemoryItem.updated_at)
        )
        await self.session.execute(stmt)
        await self.session.flush()
