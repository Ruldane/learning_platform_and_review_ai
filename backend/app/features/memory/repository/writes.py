import builtins

from sqlalchemy import Select, select

from app.db.models.memory import MemoryItem, MemoryWrite, WriteAction
from app.db.repository import UserScopedRepository

REASON_MAX = 300


class WriteRepository(UserScopedRepository[MemoryWrite]):
    """Journal des écritures de la mémoire (agents et utilisateur)."""

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
        """Note une écriture ; le titre et le type de l'élément sont copiés pour que la ligne
        survive à sa suppression."""
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
