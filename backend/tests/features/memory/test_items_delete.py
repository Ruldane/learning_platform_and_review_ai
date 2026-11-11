"""Suppression d'un élément (D66, D67) : la suppression est validée en base avant tout appel à
Qdrant ; le verrou d'écriture de SQLite n'est jamais tenu pendant le retrait des vecteurs."""

from collections.abc import Sequence

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.features.memory.repository import MemoryItemRepository
from app.features.memory.service.items import MemoryService
from app.features.memory.service.runtime import MemoryRuntime
from tests.features.memory.helpers import draft


async def test_delete_commits_before_removing_vectors(
    service: MemoryService,
    runtime: MemoryRuntime,
    db_session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = (await service.write(draft())).item
    seen: list[bool] = []
    real = runtime.indexer.unindex

    async def unindex(user_id: str, item_ids: Sequence[str]) -> None:
        async with db_session_factory() as other:  # un autre écrivain voit la suppression
            seen.append(await MemoryItemRepository(other, user_id).get(item.id) is None)
        await real(user_id, item_ids)

    monkeypatch.setattr(runtime.indexer, "unindex", unindex)
    await service.delete(item.id)
    assert seen == [True]
    records = await runtime.providers.index.vectors("u1", limit=100)
    assert [r for r in records if r.payload.item_id == item.id] == []
