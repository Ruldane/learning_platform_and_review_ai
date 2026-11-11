"""Worker de la mémoire : reprise au démarrage, jobs en série, délai, arrêt, résistance."""

import asyncio
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.providers import MemoryProviders
from app.db.models.memory import MemoryChunk, MemoryItem
from app.features.memory.repository import ChunkRepository
from app.features.memory.service import jobs as jobs_module
from app.features.memory.service.items import MemoryService
from app.features.memory.service.jobs import MemoryJobs
from app.features.memory.service.rules import WriteDraft
from app.features.memory.service.runtime import MemoryRuntime
from app.features.memory.service.sources.base import Extracted, ExtractionTools, SourceInput
from app.features.memory.service.sources.registry import INGESTION_SOURCES
from app.features.memory.service.text import chunk_text
from app.providers.vector.base import ChunkToIndex
from tests.features.memory.doc_support import PHRASE, add_document, reload
from tests.support.memory import make_chunk

USER = "u1"
Factory = async_sessionmaker[AsyncSession]
LONG = " ".join(f"mot{i}" for i in range(1200))  # trois fragments de 500 tokens


async def _vectors_for(runtime: MemoryRuntime, item_id: str) -> int:
    records = await runtime.providers.index.vectors(USER, limit=10_000)
    return sum(1 for r in records if r.payload.item_id == item_id)


async def _interrupted_document(runtime: MemoryRuntime, factory: Factory, providers: Any) -> Any:
    """Document `processing` laissé par un arrêt : élément écrit, un seul fragment en base, un
    vecteur de ce fragment et un vecteur périmé dans l'index."""
    doc = await add_document(
        factory,
        providers,
        USER,
        kind="text",
        data=LONG.encode(),
        status="processing",
        name="long.txt",
    )
    async with factory() as db:
        draft = WriteDraft(
            kind="document", title="long", text=LONG, author="user", reason="r", source_id=doc.id
        )
        item = (await MemoryService(db, USER, runtime).write(draft, index=False)).item
        rows = await ChunkRepository(db, USER).replace_for_item(item.id, chunk_text(LONG)[:1])
        await db.commit()
    stale = make_chunk(USER, "vieux", kind="document", item=item.id)
    partial = make_chunk(USER, rows[0].text, kind="document", item=item.id)
    await runtime.providers.index.index([stale, ChunkToIndex(rows[0].id, partial.payload)])
    return doc, item


async def test_processing_document_is_resumed_at_startup_without_duplicate_chunks(
    runtime: MemoryRuntime, db_session_factory: Factory, memory_providers: MemoryProviders
) -> None:
    doc, item = await _interrupted_document(runtime, db_session_factory, memory_providers)
    queued = await add_document(
        db_session_factory, memory_providers, USER, kind="text", data=PHRASE.encode()
    )
    jobs = MemoryJobs(lambda: runtime)
    await jobs.start()
    await jobs.join()
    await jobs.aclose()
    done = await reload(db_session_factory, USER, doc.id)
    assert done.status == "indexed" and done.item_id == item.id
    async with db_session_factory() as db:
        chunk_count = (
            await db.execute(select(func.count()).where(MemoryChunk.item_id == item.id))
        ).scalar_one()
        items = (await db.execute(select(func.count()).select_from(MemoryItem))).scalar_one()
    assert chunk_count == len(chunk_text(LONG)) == 3
    assert await _vectors_for(runtime, item.id) == chunk_count
    assert items == 2  # le document repris et le document en file, aucun doublon
    assert (await reload(db_session_factory, USER, queued.id)).status == "indexed"


class _Slow:
    kind = "text"

    def __init__(self, delay: float) -> None:
        self.delay = delay
        self.running = 0
        self.max_running = 0
        self.started = asyncio.Event()

    async def extract(self, source: SourceInput, tools: ExtractionTools) -> Extracted:
        self.running += 1
        self.max_running = max(self.max_running, self.running)
        self.started.set()
        try:
            await asyncio.sleep(self.delay)
        finally:
            self.running -= 1
        return Extracted(title=source.name, text=f"{PHRASE} {source.document_id}")


async def test_jobs_run_one_at_a_time(
    runtime: MemoryRuntime,
    db_session_factory: Factory,
    memory_providers: MemoryProviders,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    slow = _Slow(0.02)
    monkeypatch.setitem(INGESTION_SOURCES, "text", slow)
    docs = [
        await add_document(
            db_session_factory, memory_providers, USER, kind="text", data=f"d{i}".encode()
        )
        for i in range(3)
    ]
    for doc in docs:
        runtime.jobs.enqueue_ingest(USER, doc.id)
        runtime.jobs.enqueue_ingest(USER, doc.id)  # double mise en file : sans effet
    await runtime.jobs.join()
    assert slow.max_running == 1
    for doc in docs:
        assert (await reload(db_session_factory, USER, doc.id)).status == "indexed"


async def test_worker_survives_failing_job(
    runtime: MemoryRuntime,
    db_session_factory: Factory,
    memory_providers: MemoryProviders,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real = jobs_module.ingest
    first = await add_document(db_session_factory, memory_providers, USER, kind="text", data=b"1")
    second = await add_document(
        db_session_factory, memory_providers, USER, kind="text", data=PHRASE.encode()
    )

    async def flaky(rt: MemoryRuntime, user_id: str, document_id: str) -> None:
        if document_id == first.id:
            raise RuntimeError("panne imprévue")
        await real(rt, user_id, document_id)

    monkeypatch.setattr(jobs_module, "ingest", flaky)
    runtime.jobs.enqueue_ingest(USER, first.id)
    runtime.jobs.enqueue_ingest(USER, second.id)
    await runtime.jobs.join()
    failed = await reload(db_session_factory, USER, first.id)
    assert failed.status == "error" and failed.error is not None
    assert failed.error["code"] == "ingestion_failed"
    assert (await reload(db_session_factory, USER, second.id)).status == "indexed"


async def test_job_timeout_marks_error(
    runtime: MemoryRuntime,
    db_session_factory: Factory,
    memory_providers: MemoryProviders,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(jobs_module, "JOB_TIMEOUT_S", 0.05)
    monkeypatch.setitem(INGESTION_SOURCES, "text", _Slow(5))
    doc = await add_document(db_session_factory, memory_providers, USER, kind="text", data=b"x")
    runtime.jobs.enqueue_ingest(USER, doc.id)
    async with asyncio.timeout(3):
        await runtime.jobs.join()
    done = await reload(db_session_factory, USER, doc.id)
    assert done.status == "error" and done.error == {
        "code": "ingestion_timeout",
        "message": "L'import a dépassé 5 minutes.",
    }


async def test_aclose_stops_the_worker_and_leaves_the_document_to_resume(
    runtime: MemoryRuntime,
    db_session_factory: Factory,
    memory_providers: MemoryProviders,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    slow = _Slow(30)
    monkeypatch.setitem(INGESTION_SOURCES, "text", slow)
    doc = await add_document(db_session_factory, memory_providers, USER, kind="text", data=b"x")
    jobs = MemoryJobs(lambda: runtime)
    await jobs.start()  # reprend le document `queued`
    async with asyncio.timeout(3):
        await slow.started.wait()
        await jobs.aclose()
    assert (await reload(db_session_factory, USER, doc.id)).status == "processing"
    await jobs.aclose()  # idempotent
