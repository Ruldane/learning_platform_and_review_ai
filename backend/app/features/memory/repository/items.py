import builtins
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import ColumnElement, Select, exists, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value

from app.db.models.memory import ItemStatus, MemoryChunk, MemoryItem, MemoryKind
from app.db.repository import UserScopedRepository


@dataclass(frozen=True)
class ItemFilter:
    """List criteria: `since` and `until` bound `created_at` (inclusive)."""

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
        """Opens the write transaction before a SAVEPOINT. pysqlite only opens a transaction at the
        first write statement: without it, `begin_nested` would open one and its release would
        commit it, out of reach of a `rollback` of the request. The target row does not exist; if a
        transaction is already open, this has no effect."""
        stmt = (
            update(MemoryItem).where(MemoryItem.id == "").values(updated_at=MemoryItem.updated_at)
        )
        await self.session.execute(stmt)

    async def set_indexed_at(self, item: MemoryItem, at: datetime | None) -> None:
        """Indexing date of `item` (`None`: to re-index); `updated_at` is not touched, since
        indexing an item is not modifying it."""
        stmt = (
            update(MemoryItem)
            .where(MemoryItem.id == item.id, MemoryItem.user_id == self.user_id)
            .values(indexed_at=at, updated_at=MemoryItem.updated_at)
        )
        await self.session.execute(stmt)
        set_committed_value(item, "indexed_at", at)

    async def mark_indexed(self, item: MemoryItem, at: datetime, chunk_id: str | None) -> bool:
        """Sets `indexed_at` only if the item still exists and if `chunk_id` (a fragment just pushed
        to the index) still belongs to it in the database: otherwise its fragments were renewed in
        the meantime (concurrent write) and the index is no longer up to date. True if it was done.
        `None`: item without a fragment, no condition."""
        conditions = [MemoryItem.id == item.id, MemoryItem.user_id == self.user_id]
        if chunk_id is not None:
            conditions.append(
                exists().where(
                    MemoryChunk.id == chunk_id,
                    MemoryChunk.item_id == item.id,
                    MemoryChunk.user_id == self.user_id,
                )
            )
        stmt = (
            update(MemoryItem)
            .where(*conditions)
            .values(indexed_at=at, updated_at=MemoryItem.updated_at)
            .returning(MemoryItem.id)
            .execution_options(synchronize_session=False)
        )
        if (await self.session.execute(stmt)).first() is None:
            return False
        set_committed_value(item, "indexed_at", at)
        return True

    async def find_by_hash(self, content_hash: str) -> MemoryItem | None:
        stmt = select(MemoryItem).where(
            MemoryItem.user_id == self.user_id, MemoryItem.content_hash == content_hash
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def find_document_of(self, source_id: str) -> MemoryItem | None:
        """Item `document` from the document `source_id` (the oldest if there are several)."""
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
        """Items that match `f`, most recent first, and their total count (without `limit` or
        `offset`)."""
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
        """Active items not yet indexed in Qdrant."""
        stmt = select(func.count()).select_from(
            self._scoped().where(MemoryItem.indexed_at.is_(None)).subquery()
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def active(self, *, limit: int | None = None) -> builtins.list[MemoryItem]:
        stmt = self._scoped().order_by(MemoryItem.created_at.desc(), MemoryItem.id.desc())
        if limit is not None:
            stmt = stmt.limit(limit)
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def of_kind(self, kind: MemoryKind) -> builtins.list[MemoryItem]:
        """Active items of a type, from oldest to newest (no limit)."""
        stmt = (
            self._scoped()
            .where(MemoryItem.kind == kind)
            .order_by(MemoryItem.created_at, MemoryItem.id)
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def everything(self) -> builtins.list[MemoryItem]:
        """All items, active and pending, most recent first (export)."""
        stmt = (
            select(MemoryItem)
            .where(MemoryItem.user_id == self.user_id)
            .order_by(MemoryItem.created_at.desc(), MemoryItem.id.desc())
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def unindexed_batch(self, limit: int) -> builtins.list[MemoryItem]:
        """Active items to index, from oldest to newest."""
        stmt = (
            self._scoped()
            .where(MemoryItem.indexed_at.is_(None))
            .order_by(MemoryItem.created_at, MemoryItem.id)
            .limit(limit)
        )
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def clear_indexed(self) -> None:
        """Marks all active items as to be re-indexed (`updated_at` is not touched)."""
        stmt = (
            update(MemoryItem)
            .where(MemoryItem.user_id == self.user_id, MemoryItem.status == "active")
            .values(indexed_at=None, updated_at=MemoryItem.updated_at)
        )
        await self.session.execute(stmt)
        await self.session.flush()


async def users_with_unindexed(session: AsyncSession, limit: int) -> builtins.list[str]:
    """Accounts that have active items to index (at most `limit`), identifiers only.

    The ONLY read without `user_id` on memory (like `validated_programs`): reserved for the
    maintenance task that catches up on indexing (`index_pending_all`); every following read
    filters by user."""
    stmt = (
        select(MemoryItem.user_id)
        .where(MemoryItem.status == "active", MemoryItem.indexed_at.is_(None))
        .group_by(MemoryItem.user_id)
        .limit(limit)
    )
    return builtins.list((await session.execute(stmt)).scalars().all())
