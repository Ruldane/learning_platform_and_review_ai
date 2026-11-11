"""Vecteurs orphelins (M2 de la phase 2, D71) : un document supprimé pendant que l'import pousse
ses vecteurs ne laisse rien dans l'index ; une panne du magasin à ce moment est avalée et
journalisée par identifiant seulement."""

import asyncio
import logging
from collections.abc import Sequence
from dataclasses import replace
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.providers import MemoryProviders
from app.features.memory.repository import DocumentRepository, MemoryItemRepository
from app.features.memory.service.items import MemoryService
from app.features.memory.service.pipeline import ingest
from app.features.memory.service.runtime import memory_runtime
from app.providers.vector.base import ChunkToIndex, VectorStoreUnavailable
from tests.features.memory.doc_support import PHRASE, add_document, reload

USER = "u1"
Factory = async_sessionmaker[AsyncSession]


class _HeldIndex:
    """L'index réel, dont `index` attend `release` ; `broken` : `delete_items` en panne."""

    def __init__(self, real: Any) -> None:
        self._real = real
        self.entered, self.release = asyncio.Event(), asyncio.Event()
        self.broken = False

    async def index(self, chunks: Sequence[ChunkToIndex]) -> None:
        self.entered.set()
        await self.release.wait()
        await self._real.index(chunks)

    async def delete_items(self, user_id: str, item_ids: Sequence[str]) -> None:
        if self.broken:
            raise VectorStoreUnavailable()
        await self._real.delete_items(user_id, item_ids)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._real, name)


async def _delete_during_push(
    factory: Factory, providers: MemoryProviders, held: _HeldIndex, *, break_store: bool
) -> tuple[str, str]:
    """Import lancé, bloqué dans `index` ; l'élément du document est supprimé (comme
    `DELETE /memory/items/{id}`) ; puis l'index repart. Rend (document, élément)."""
    async with memory_runtime(factory, providers) as rt:
        doc = await add_document(factory, providers, USER, kind="text", data=PHRASE.encode())
        worker = asyncio.create_task(ingest(rt, USER, doc.id))
        await asyncio.wait_for(held.entered.wait(), 3)
        item_id = (await reload(factory, USER, doc.id)).item_id
        assert item_id is not None
        async with factory() as db:
            await MemoryService(db, USER, rt).delete(item_id)
        held.broken = break_store
        held.release.set()
        await asyncio.wait_for(worker, 5)
    return doc.id, item_id


async def test_document_deleted_during_import_leaves_no_vector(
    db_session_factory: Factory, memory_providers: MemoryProviders
) -> None:
    held = _HeldIndex(memory_providers.index)
    providers = replace(memory_providers, index=held)
    doc_id, item_id = await _delete_during_push(
        db_session_factory, providers, held, break_store=False
    )
    assert await memory_providers.index.vectors(USER, limit=100) == []
    async with db_session_factory() as db:
        assert await DocumentRepository(db, USER).get(doc_id) is None
        assert await MemoryItemRepository(db, USER).get(item_id) is None


async def test_orphan_cleanup_swallows_store_failure_and_logs_ids_only(
    db_session_factory: Factory,
    memory_providers: MemoryProviders,
    caplog: pytest.LogCaptureFixture,
) -> None:
    held = _HeldIndex(memory_providers.index)
    providers = replace(memory_providers, index=held)
    with caplog.at_level(logging.INFO):
        _, item_id = await _delete_during_push(
            db_session_factory, providers, held, break_store=True
        )
    warnings = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
    assert any(item_id in message for message in warnings)
    assert "transformeurs" not in caplog.text.lower() and "cours" not in caplog.text
