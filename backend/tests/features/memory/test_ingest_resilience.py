"""Résistance de l'indexation (D66) : aucune écriture ne tient le verrou d'écriture de SQLite en
attendant l'index, un statut final refusé par SQLite est réessayé, une source relue dont le
contenu a changé met à jour l'élément au lieu de le doubler, un fichier disparu est lisible."""

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import replace
from typing import Any

import pytest
from qdrant_client import AsyncQdrantClient
from sqlalchemy import func, select, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.providers import MemoryProviders
from app.db.models.memory import Document, MemoryChunk, MemoryItem
from app.features.memory.repository import DocumentRepository, MemoryItemRepository, WriteRepository
from app.features.memory.schemas import SearchRequest
from app.features.memory.service import ingest_steps
from app.features.memory.service.items import MemoryService
from app.features.memory.service.pipeline import ingest
from app.features.memory.service.runtime import MemoryRuntime, memory_runtime
from app.features.memory.service.search import search
from app.providers.embeddings.fake import HashingEmbedder
from app.providers.vector.qdrant import QdrantMemoryRepository
from app.providers.web.base import WebDocument
from tests.features.memory.doc_support import PHRASE, add_document, reload
from tests.features.memory.helpers import draft, with_embeddings_down
from tests.support.memory import FAKE_DIMENSION, FakeWebReader

USER = "u1"
URL = "https://example.org/article"
OTHER = "Les réseaux convolutifs détectent des motifs locaux dans les images."
Factory = async_sessionmaker[AsyncSession]


class _Gated(HashingEmbedder):
    """La première vectorisation attend `release` : le worker reste dans `push`, verrou de
    l'utilisateur pris."""

    def __init__(self) -> None:
        super().__init__(FAKE_DIMENSION)
        self.entered, self.release = asyncio.Event(), asyncio.Event()
        self._first = True

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        if self._first:
            self._first = False
            self.entered.set()
            await self.release.wait()
        return await super().aembed_documents(texts)


async def _until(check: Callable[[], Awaitable[bool]], timeout: float = 3.0) -> None:
    async with asyncio.timeout(timeout):
        while not await check():
            await asyncio.sleep(0.01)


async def test_request_write_never_holds_the_write_lock_while_the_worker_pushes(
    db_session_factory: Factory, memory_providers: MemoryProviders
) -> None:
    gated = _Gated()
    index = QdrantMemoryRepository(
        AsyncQdrantClient(location=":memory:"), gated, collection="memory", dimension=64
    )
    providers = replace(memory_providers, embedder=gated, index=index)
    async with memory_runtime(db_session_factory, providers) as rt:
        doc = await add_document(
            db_session_factory, providers, USER, kind="text", data=PHRASE.encode()
        )
        worker = asyncio.create_task(ingest(rt, USER, doc.id))
        await asyncio.wait_for(gated.entered.wait(), 3)

        async def request_write() -> Any:
            async with db_session_factory() as db:
                return await MemoryService(db, USER, rt).write(draft(title="Autre", text=OTHER))

        request = asyncio.create_task(request_write())

        async def committed() -> bool:
            async with db_session_factory() as db:
                stmt = select(func.count()).where(MemoryItem.title == "Autre")
                return bool((await db.execute(stmt)).scalar_one())

        await _until(committed)  # la requête a validé avant d'attendre le verrou de l'index
        start = time.monotonic()
        async with db_session_factory() as db:  # un autre écrivain (bus, runner) passe aussitôt
            await db.execute(update(Document).where(Document.id == "").values(name="x"))
            await db.commit()
        assert time.monotonic() - start < 1.0 and not request.done()
        gated.release.set()
        await worker
        outcome = await request
    assert outcome.item.indexed_at is not None
    assert (await reload(db_session_factory, USER, doc.id)).status == "indexed"


async def test_embed_failure_after_commit_keeps_the_item_readable_and_reindexable(
    db_session_factory: Factory, memory_providers: MemoryProviders, runtime: MemoryRuntime
) -> None:
    down_providers = with_embeddings_down(memory_providers)
    async with (
        memory_runtime(db_session_factory, down_providers) as down,
        db_session_factory() as db,
    ):
        out = await MemoryService(db, USER, down).write(draft())
        await db.rollback()  # validé avant la vectorisation : rien n'est perdu
    async with db_session_factory() as db:
        items = MemoryItemRepository(db, USER)
        item = await items.get(out.item.id)
        assert item is not None and item.indexed_at is None
        assert [i.id for i in await items.unindexed_batch(10)] == [item.id]
        assert await runtime.indexer.index_item(db, item) is True  # ce que fera la réindexation
        found = await search(db, USER, runtime, SearchRequest(query="attention"))
    assert [h.item_id for h in found.hits] == [item.id]


def _locked() -> OperationalError:
    return OperationalError("UPDATE", {}, Exception("database is locked"))


def _flaky(real: Callable[..., Awaitable[None]], failures: int, calls: list[int]) -> Any:
    async def step(*args: Any, **kwargs: Any) -> None:
        calls.append(1)
        if len(calls) <= failures:
            raise _locked()
        await real(*args, **kwargs)

    return step


async def test_final_status_is_retried_when_sqlite_is_locked(
    runtime: MemoryRuntime,
    db_session_factory: Factory,
    memory_providers: MemoryProviders,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ingest_steps, "RETRY_BACKOFF_S", 0)
    calls: list[int] = []
    monkeypatch.setattr(ingest_steps, "finish_once", _flaky(ingest_steps.finish_once, 2, calls))
    doc = await add_document(
        db_session_factory, memory_providers, USER, kind="text", data=PHRASE.encode()
    )
    await ingest(runtime, USER, doc.id)
    assert len(calls) == 3 and (await reload(db_session_factory, USER, doc.id)).status == "indexed"


async def test_mark_error_is_retried_then_gives_up(
    runtime: MemoryRuntime,
    db_session_factory: Factory,
    memory_providers: MemoryProviders,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ingest_steps, "RETRY_BACKOFF_S", 0)
    real, calls = ingest_steps.mark_error_once, []
    monkeypatch.setattr(ingest_steps, "mark_error_once", _flaky(real, 1, calls))
    short = await add_document(db_session_factory, memory_providers, USER, kind="text", data=b"x")
    await ingest(runtime, USER, short.id)
    done = await reload(db_session_factory, USER, short.id)
    assert len(calls) == 2 and done.error is not None and done.error["code"] == "no_text"
    stuck: list[int] = []
    monkeypatch.setattr(ingest_steps, "mark_error_once", _flaky(real, 99, stuck))
    other = await add_document(db_session_factory, memory_providers, USER, kind="text", data=b"y")
    with pytest.raises(OperationalError):
        await ingest(runtime, USER, other.id)  # le worker le journalise ; un réimport le relance
    assert len(stuck) == 3


async def test_changed_link_content_updates_the_same_item(
    runtime: MemoryRuntime, db_session_factory: Factory, memory_providers: MemoryProviders
) -> None:
    web = memory_providers.web
    assert isinstance(web, FakeWebReader)
    web.pages[URL] = WebDocument(URL, "Article", PHRASE, None, None, None, None)
    doc = await add_document(
        db_session_factory, memory_providers, USER, kind="url", url=URL, name="example.org"
    )
    await ingest(runtime, USER, doc.id)
    web.pages[URL] = WebDocument(URL, "Article", OTHER, None, None, None, None)
    async with db_session_factory() as db:  # reprise (ou réimport) : nouvelle lecture du lien
        await DocumentRepository(db, USER).update(doc.id, status="processing")
        await db.commit()
    await ingest(runtime, USER, doc.id)
    done = await reload(db_session_factory, USER, doc.id)
    async with db_session_factory() as db:
        items = (await db.execute(select(MemoryItem))).scalars().all()
        chunks = (await db.execute(select(MemoryChunk))).scalars().all()
        writes = await WriteRepository(db, USER).all()
    vectors = await runtime.providers.index.vectors(USER, limit=100)
    assert done.status == "indexed" and [i.id for i in items] == [done.item_id]
    assert items[0].text == OTHER and [c.text for c in chunks] == [OTHER]
    assert [v.payload.text for v in vectors] == [OTHER]
    assert [w.action for w in writes] == ["update", "create"]


async def test_missing_stored_file_is_a_readable_error(
    runtime: MemoryRuntime, db_session_factory: Factory, memory_providers: MemoryProviders
) -> None:
    doc = await add_document(
        db_session_factory, memory_providers, USER, kind="text", data=PHRASE.encode()
    )
    assert doc.storage_key is not None
    await memory_providers.storage.delete(USER, doc.storage_key)
    await ingest(runtime, USER, doc.id)
    done = await reload(db_session_factory, USER, doc.id)
    assert done.error == {
        "code": "document_source_missing",
        "message": "Fichier ou lien d'origine introuvable : importe ce document de nouveau.",
    }


async def test_import_end_never_marks_an_item_indexed_after_its_chunks_changed(
    db_session_factory: Factory, memory_providers: MemoryProviders, runtime: MemoryRuntime
) -> None:
    """Une modification (PATCH) renouvelle les fragments pendant le `push` de l'import : la fin
    de l'import ne pose pas `indexed_at` (ses vecteurs sont périmés), l'élément reste à
    rattraper ; le document est bien `indexed`."""
    doc = await add_document(
        db_session_factory, memory_providers, USER, kind="text", data=PHRASE.encode()
    )
    claimed = await ingest_steps.claim(runtime, USER, doc.id)
    assert claimed is not None
    written = await ingest_steps.write_item(runtime, claimed, "Cours", PHRASE, None)
    assert written.chunks
    await runtime.indexer.push(USER, written.item_id, written.chunks)
    async with db_session_factory() as db:  # écriture concurrente : nouveaux fragments
        item = await MemoryItemRepository(db, USER).get(written.item_id)
        assert item is not None
        await runtime.indexer.prepare(db, item)
        await db.commit()
    await ingest_steps.finish_once(runtime, claimed, written, "Cours", None)
    async with db_session_factory() as db:
        item = await MemoryItemRepository(db, USER).get(written.item_id)
    assert item is not None and item.indexed_at is None
    assert (await reload(db_session_factory, USER, doc.id)).status == "indexed"
