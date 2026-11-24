"""Reading a user's rows, table by table.

Documented exception to `UserScopedRepository`: the export walks **every** table that has
`user_id` (one more table changes nothing), so it has no fixed model; every read still filters
on `user_id`, always."""

from collections.abc import AsyncGenerator, Sequence
from typing import Any

from sqlalchemy import Column, Select, Table, delete, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.accounts import AccountVectorPurge


class AccountRepository:
    def __init__(self, session: AsyncSession, user_id: str) -> None:
        self.session = session
        self.user_id = user_id

    def _select(self, table: Table, columns: Sequence[Column[Any]] | None) -> Select[Any]:
        """The rows of `user_id`, ordered by creation then by id. Only the given `columns` are
        read (all by default): an excluded column never enters memory."""
        stmt = select(*(table.c if columns is None else columns)).where(
            table.c.user_id == self.user_id
        )
        order = [table.c[name] for name in ("created_at", "id") if name in table.c]
        return stmt.order_by(*order)

    async def batches(
        self, table: Table, columns: Sequence[Column[Any]] | None, size: int
    ) -> AsyncGenerator[list[dict[str, Any]], None]:
        """The rows of `user_id` in batches of at most `size`: never more than one batch in
        memory, whatever the size of the table."""
        stream = await self.session.stream(
            self._select(table, columns).execution_options(yield_per=size)
        )
        try:
            async for batch in stream.mappings().partitions(size):
                yield [dict(row) for row in batch]
        finally:
            await stream.close()

    async def rows(
        self, table: Table, columns: Sequence[Column[Any]] | None = None
    ) -> list[dict[str, Any]]:
        """All rows at once, for a small table (an account's sessions). The export reads in
        batches (`batches`)."""
        result = await self.session.execute(self._select(table, columns))
        return [dict(row) for row in result.mappings()]


async def queue_vector_purge(db: AsyncSession, user_id: str) -> None:
    await db.execute(
        insert(AccountVectorPurge)
        .values(user_id=user_id)
        .on_conflict_do_nothing(index_elements=[AccountVectorPurge.user_id])
    )


async def complete_vector_purge(db: AsyncSession, user_id: str) -> None:
    await db.execute(delete(AccountVectorPurge).where(AccountVectorPurge.user_id == user_id))


async def pending_vector_purges(db: AsyncSession) -> list[str]:
    """The scheduler's work queue, independent of accounts and free of user content."""
    result = await db.scalars(
        select(AccountVectorPurge.user_id).order_by(AccountVectorPurge.created_at)
    )
    return list(result)
