"""Journal (SPEC F18): writes go through `INSERT … ON CONFLICT DO NOTHING`, so that a replay
(or two simultaneous requests) of the same `ref_key` never raises a uniqueness error. Reads go
from newest to oldest (`created_at`, then insertion order)."""

import builtins
from typing import Any

from sqlalchemy import ColumnElement, and_, literal_column, or_, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.db.models.study import JournalEntry
from app.db.repository import UserScopedRepository


class JournalRepository(UserScopedRepository[JournalEntry]):
    model = JournalEntry

    async def insert_once(self, ref_key: str | None, **fields: Any) -> str:
        """Writes the row and returns its id; if `ref_key` already exists for this user, returns
        the id of the existing row without changing anything. Without `ref_key`, the row is
        always new."""
        stmt = (
            sqlite_insert(JournalEntry)
            .values(user_id=self.user_id, ref_key=ref_key, **fields)
            .on_conflict_do_nothing(index_elements=["user_id", "ref_key"])
            .returning(JournalEntry.id)
        )
        created = (await self.session.execute(stmt)).scalar_one_or_none()
        if created is not None:
            return created
        existing = select(JournalEntry.id).where(
            JournalEntry.user_id == self.user_id, JournalEntry.ref_key == ref_key
        )
        return (await self.session.execute(existing)).scalar_one()

    async def by_ref(self, ref_key: str) -> JournalEntry | None:
        stmt = select(JournalEntry).where(
            JournalEntry.user_id == self.user_id, JournalEntry.ref_key == ref_key
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def page(
        self, kind: str | None, before: str | None, limit: int
    ) -> builtins.list[JournalEntry] | None:
        """Up to `limit` rows, most recent first, older than the `before` row (cursor); `None`
        if this cursor is not a row of the user."""
        rowid: ColumnElement[int] = literal_column("rowid")
        stmt = select(JournalEntry).where(JournalEntry.user_id == self.user_id)
        if kind is not None:
            stmt = stmt.where(JournalEntry.kind == kind)
        if before is not None:
            cursor = (
                await self.session.execute(
                    select(JournalEntry.created_at, rowid).where(
                        JournalEntry.user_id == self.user_id, JournalEntry.id == before
                    )
                )
            ).first()
            if cursor is None:
                return None
            at, seq = cursor
            stmt = stmt.where(
                or_(
                    JournalEntry.created_at < at,
                    and_(JournalEntry.created_at == at, rowid < seq),
                )
            )
        stmt = stmt.order_by(JournalEntry.created_at.desc(), rowid.desc()).limit(limit)
        return builtins.list((await self.session.execute(stmt)).scalars().all())
