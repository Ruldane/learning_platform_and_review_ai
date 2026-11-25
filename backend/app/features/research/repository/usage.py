from datetime import datetime
from typing import Any

from sqlalchemy import Select, func, literal, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import new_id, utcnow
from app.db.models.research import SearchUsage
from app.db.repository import UserScopedRepository


class SearchUsageRepository(UserScopedRepository[SearchUsage]):
    """A user's monthly counter, per provider and per key."""

    model = SearchUsage

    async def increment(self, provider: str, month: str, fingerprint: str) -> None:
        """Adds 1 to the counter in a single statement: no lost read-write."""
        stmt = sqlite_insert(SearchUsage).values(
            user_id=self.user_id,
            provider=provider,
            month=month,
            key_fingerprint=fingerprint,
            count=1,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "provider", "month", "key_fingerprint"],
            set_={"count": SearchUsage.count + 1, "updated_at": stmt.excluded.updated_at},
        )
        await self.session.execute(stmt)

    async def reserve(self, provider: str, month: str, fingerprint: str, cap: int) -> bool:
        """Adds 1 to the user's counter only if the month's total for this key (all users, like
        `month_total`) is under `cap`. A single statement, `INSERT … SELECT … WHERE total < cap ON
        CONFLICT DO UPDATE`: SQLite runs it under its write lock, so the check and the addition are
        indivisible, even across processes. Returns true if a query was reserved."""
        now: datetime = utcnow()
        values = select(
            literal(new_id()),
            literal(self.user_id),
            literal(provider),
            literal(month),
            literal(fingerprint),
            literal(1),
            literal(now, SearchUsage.created_at.type),
            literal(now, SearchUsage.updated_at.type),
        ).where(_total(provider, month, fingerprint).scalar_subquery() < cap)
        columns = ["id", "user_id", "provider", "month", "key_fingerprint", "count"]
        stmt = sqlite_insert(SearchUsage).from_select(
            [*columns, "created_at", "updated_at"], values
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "provider", "month", "key_fingerprint"],
            set_={"count": SearchUsage.count + 1, "updated_at": stmt.excluded.updated_at},
        )
        result = await self.session.execute(stmt)
        return int(result.rowcount or 0) == 1  # type: ignore[attr-defined]

    async def release(self, provider: str, month: str, fingerprint: str) -> bool:
        """Returns a reserved query that the provider did not serve: `count - 1` on the user's only
        row, in a statement guarded by `count > 0` (never negative, never on another user's count).
        Returns true if a query was returned."""
        stmt = (
            update(SearchUsage)
            .where(
                SearchUsage.user_id == self.user_id,
                SearchUsage.provider == provider,
                SearchUsage.month == month,
                SearchUsage.key_fingerprint == fingerprint,
                SearchUsage.count > 0,
            )
            .values(count=SearchUsage.count - 1, updated_at=utcnow())
        )
        result = await self.session.execute(stmt)
        return int(result.rowcount or 0) == 1  # type: ignore[attr-defined]


def _total(provider: str, month: str, fingerprint: str) -> Select[Any]:
    return select(func.coalesce(func.sum(SearchUsage.count), 0)).where(
        SearchUsage.provider == provider,
        SearchUsage.month == month,
        SearchUsage.key_fingerprint == fingerprint,
    )


async def month_total(db: AsyncSession, *, provider: str, month: str, fingerprint: str) -> int:
    """The month's queries for one key, all users combined (D75).

    The only read of the phase without a `user_id` filter: a `.env` key is shared by all users in
    Google mode, and its cap is that of the Brave account, not of a user.
    Returns only a number, never a row or a user identifier.
    """
    return int((await db.execute(_total(provider, month, fingerprint))).scalar_one())
