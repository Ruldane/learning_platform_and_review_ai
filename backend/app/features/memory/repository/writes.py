import builtins
from datetime import datetime

from sqlalchemy import Select, and_, func, not_, or_, select

from app.db.models.memory import USER_AUTHOR, MemoryItem, MemoryWrite, WriteAction
from app.db.repository import UserScopedRepository

REASON_MAX = 300


class WriteRepository(UserScopedRepository[MemoryWrite]):
    """Write log of the memory (agents and user)."""

    model = MemoryWrite

    async def log(
        self,
        *,
        item: MemoryItem,
        action: WriteAction,
        author: str,
        session_id: str | None,
        reason: str | None,
    ) -> MemoryWrite:
        """Records a write; the item's title and kind are copied so the row survives its
        deletion."""
        return await self.add(
            item_id=item.id,
            item_title=item.title,
            kind=item.kind,
            action=action,
            author=author,
            session_id=session_id,
            reason=reason[:REASON_MAX] if reason is not None else None,
        )

    def _ordered(self) -> Select[MemoryWrite]:
        return (
            select(MemoryWrite)
            .where(MemoryWrite.user_id == self.user_id)
            .order_by(MemoryWrite.created_at.desc(), MemoryWrite.id.desc())
        )

    async def for_item(self, item_id: str) -> builtins.list[MemoryWrite]:
        stmt = self._ordered().where(MemoryWrite.item_id == item_id)
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def last(self) -> MemoryWrite | None:
        return (await self.session.execute(self._ordered().limit(1))).scalar_one_or_none()

    async def all(self) -> builtins.list[MemoryWrite]:
        return builtins.list((await self.session.execute(self._ordered())).scalars().all())

    async def by_agents_between(
        self,
        after: datetime | None,
        before: datetime | None,
        limit: int,
        *,
        skip: tuple[str, tuple[str, ...], tuple[str, ...]],
    ) -> builtins.list[MemoryWrite]:
        """Agent writes (author other than the user, deletions excluded) within `[after, before]`
        (inclusive bounds), most recent first. Exclude the given author's writes when their
        reason matches a capture reason or prefix in `skip`."""
        author, reasons, prefixes = skip
        why = func.coalesce(MemoryWrite.reason, "")
        capture_reason = or_(why.in_(reasons), *(why.startswith(prefix) for prefix in prefixes))
        stmt = self._ordered().where(
            MemoryWrite.author != USER_AUTHOR,
            MemoryWrite.action != "delete",
            not_(and_(MemoryWrite.author == author, capture_reason)),
        )
        if after is not None:
            stmt = stmt.where(MemoryWrite.created_at >= after)
        if before is not None:
            stmt = stmt.where(MemoryWrite.created_at <= before)
        return builtins.list((await self.session.execute(stmt.limit(limit))).scalars())
