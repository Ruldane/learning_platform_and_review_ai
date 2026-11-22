"""Données de lecture filtrées par propriétaire et plis de collecte idempotents."""

from dataclasses import asdict
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert

from app.db.models.reading_stack import ReadingItem, ReadingKind, ReadingSource
from app.db.repository import UserScopedRepository
from app.features.reading_stack.types import CollectedItem


class ReadingRepository(UserScopedRepository[ReadingItem]):
    model = ReadingItem

    async def record(self, item: CollectedItem, now: datetime) -> str | None:
        stmt = (
            insert(ReadingItem)
            .values(**asdict(item), user_id=self.user_id, created_at=now, updated_at=now)
            .on_conflict_do_nothing(index_elements=["user_id", "url"])
            .returning(ReadingItem.id)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def mark_read(self, item_id: str, read: bool, now: datetime) -> ReadingItem | None:
        row = await self.get(item_id)
        if row is not None and read != (row.read_at is not None):
            row.read_at = now if read else None
            await self.session.flush()
        return row

    async def items(
        self,
        *,
        unread: bool | None = None,
        kind: ReadingKind | None = None,
        offset: int = 0,
    ) -> list[ReadingItem]:
        stmt = select(ReadingItem).where(ReadingItem.user_id == self.user_id)
        if unread is True:
            stmt = stmt.where(ReadingItem.read_at.is_(None))
        if unread is False:
            stmt = stmt.where(ReadingItem.read_at.is_not(None))
        if kind is not None:
            stmt = stmt.where(ReadingItem.kind == kind)
        stmt = stmt.order_by(ReadingItem.created_at.desc(), ReadingItem.id.desc())
        return list((await self.session.scalars(stmt.offset(offset).limit(50))).all())

    async def unread_count(self) -> int:
        stmt = select(func.count()).select_from(ReadingItem)
        stmt = stmt.where(ReadingItem.user_id == self.user_id, ReadingItem.read_at.is_(None))
        return (await self.session.execute(stmt)).scalar_one()

    async def recent_urls(self) -> set[str]:
        stmt = (
            select(ReadingItem.url)
            .where(ReadingItem.user_id == self.user_id)
            .order_by(ReadingItem.created_at.desc())
            .limit(500)
        )
        return set((await self.session.scalars(stmt)).all())


class ReadingSources(UserScopedRepository[ReadingSource]):
    model = ReadingSource
