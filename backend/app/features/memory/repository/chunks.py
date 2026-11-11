import builtins
from collections.abc import Sequence
from typing import Protocol

from sqlalchemy import delete, func, select

from app.db.models.memory import MemoryChunk
from app.db.repository import UserScopedRepository


class ChunkDraftLike(Protocol):
    """Forme d'un fragment à enregistrer (`service.text.ChunkDraft`) : la couche repository
    ne peut pas importer la couche service, le typage structurel les relie."""

    @property
    def ordinal(self) -> int: ...
    @property
    def text(self) -> str: ...
    @property
    def token_count(self) -> int: ...


class ChunkRepository(UserScopedRepository[MemoryChunk]):
    model = MemoryChunk

    async def replace_for_item(
        self, item_id: str, drafts: Sequence[ChunkDraftLike]
    ) -> builtins.list[MemoryChunk]:
        """Remplace tous les fragments de l'élément (nouveaux `id` : l'appelant renouvelle
        aussi les points de Qdrant)."""
        await self.session.execute(
            delete(MemoryChunk).where(
                MemoryChunk.user_id == self.user_id, MemoryChunk.item_id == item_id
            )
        )
        rows = [
            MemoryChunk(
                user_id=self.user_id,
                item_id=item_id,
                ordinal=d.ordinal,
                text=d.text,
                token_count=d.token_count,
            )
            for d in drafts
        ]
        self.session.add_all(rows)
        await self.session.flush()
        return rows

    async def for_item(self, item_id: str, limit: int | None = None) -> builtins.list[MemoryChunk]:
        """Fragments de l'élément dans l'ordre ; `limit` : les premiers seulement."""
        stmt = (
            select(MemoryChunk)
            .where(MemoryChunk.user_id == self.user_id, MemoryChunk.item_id == item_id)
            .order_by(MemoryChunk.ordinal)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        return builtins.list((await self.session.execute(stmt)).scalars().all())

    async def get_many(self, ids: Sequence[str]) -> dict[str, MemoryChunk]:
        if not ids:
            return {}
        stmt = select(MemoryChunk).where(
            MemoryChunk.user_id == self.user_id, MemoryChunk.id.in_(builtins.list(ids))
        )
        return {row.id: row for row in (await self.session.execute(stmt)).scalars()}

    async def count(self) -> int:
        stmt = select(func.count()).where(MemoryChunk.user_id == self.user_id)
        return int((await self.session.execute(stmt)).scalar_one())
