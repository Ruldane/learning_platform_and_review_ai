"""Chaîne d'ingestion d'un document : extraction, écriture, indexation, statuts et erreurs."""

import logging
import time
from collections.abc import AsyncIterator
from dataclasses import replace

import pytest
from qdrant_client import AsyncQdrantClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.providers import MemoryProviders
from app.db.models.memory import Document
from app.features.memory.repository import ChunkRepository, MemoryItemRepository
from app.features.memory.schemas import SearchRequest
from app.features.memory.service.pipeline import ingest
from app.features.memory.service.runtime import MemoryRuntime, memory_runtime
from app.features.memory.service.search import search
from app.features.memory.service.sources.base import Extracted, ExtractionTools, SourceInput
from app.features.memory.service.sources.registry import INGESTION_SOURCES
from app.providers.embeddings.fake import HashingEmbedder
from app.providers.vector.qdrant import QdrantMemoryRepository
from app.providers.web.base import UrlForbidden, WebDocument
from scripts.sample_pdf import make_pdf
from tests.features.memory.doc_support import PHRASE, add_document, reload
from tests.features.memory.helpers import with_embeddings_down, with_vector_store_down
from tests.support.memory import FAKE_DIMENSION, FakeWebReader

USER = "u1"
Factory = async_sessionmaker[AsyncSession]


async def test_ingest_pdf_indexes_and_search_finds_it(
    runtime: MemoryRuntime, db_session_factory: Factory, memory_providers: MemoryProviders
) -> None:
    doc = await add_document(
        db_session_factory,
        memory_providers,
        USER,
        kind="pdf",
        data=make_pdf([PHRASE]),
        suffix=".pdf",
    )
    await ingest(runtime, USER, doc.id)
    done = await reload(db_session_factory, USER, doc.id)
    assert done.status == "indexed" and done.error is None and done.item_id is not None
    async with db_session_factory() as db:
        res = await search(db, USER, runtime, SearchRequest(query="attention multi-têtes"))
        item = await MemoryItemRepository(db, USER).get(done.item_id)
    assert res.hits[0].item_id == done.item_id and res.hits[0].kind == "document"
    assert item is not None and item.source_id == doc.id and item.title == "cours"
    assert item.created_by == "user" and item.meta["reason"] == "Import du document « cours.pdf »."
    assert item.indexed_at is not None


async def test_ingest_ignores_documents_already_done(
    runtime: MemoryRuntime, db_session_factory: Factory, memory_providers: MemoryProviders
) -> None:
    doc = await add_document(
        db_session_factory,
        memory_providers,
        USER,
        kind="text",
        data=PHRASE.encode(),
        status="indexed",
    )
    await ingest(runtime, USER, doc.id)
    await ingest(runtime, "autre", doc.id)  # document d'un autre : introuvable, rien
    assert (await reload(db_session_factory, USER, doc.id)).item_id is None


async def test_empty_text_marks_error_no_text(
    runtime: MemoryRuntime, db_session_factory: Factory, memory_providers: MemoryProviders
) -> None:
    doc = await add_document(
        db_session_factory,
        memory_providers,
        USER,
        kind="text",
        data=b"  court \n\n  ",
    )
    await ingest(runtime, USER, doc.id)
    done = await reload(db_session_factory, USER, doc.id)
    assert done.status == "error" and done.error == {
        "code": "no_text",
        "message": "Aucun texte trouvé dans ce document (PDF scanné ?).",
    }


async def test_duplicate_content_marks_error_with_existing_title(
    runtime: MemoryRuntime, db_session_factory: Factory, memory_providers: MemoryProviders
) -> None:
    first = await add_document(
        db_session_factory,
        memory_providers,
        USER,
        kind="text",
        data=PHRASE.encode(),
        name="premier.txt",
    )
    await ingest(runtime, USER, first.id)
    second = await add_document(
        db_session_factory,
        memory_providers,
        USER,
        kind="paste",
        data=f" {PHRASE} ".encode(),
        name="Copie",
    )
    await ingest(runtime, USER, second.id)
    item_id = (await reload(db_session_factory, USER, first.id)).item_id
    done = await reload(db_session_factory, USER, second.id)
    assert done.status == "error" and done.item_id is None
    assert done.error == {
        "code": "duplicate_content",
        "message": "Ce contenu est déjà en mémoire (« premier »).",
        "item_id": item_id,
    }


@pytest.fixture(params=["embeddings", "vector_store"])
async def runtime_down(
    request: pytest.FixtureRequest, db_session_factory: Factory, memory_providers: MemoryProviders
) -> AsyncIterator[MemoryRuntime]:
    down = (
        with_embeddings_down(memory_providers)
        if request.param == "embeddings"
        else with_vector_store_down(memory_providers)
    )
    async with memory_runtime(db_session_factory, down) as rt:
        yield rt


async def test_ingestion_marks_error_when_embeddings_down(
    runtime_down: MemoryRuntime, db_session_factory: Factory, memory_providers: MemoryProviders
) -> None:
    doc = await add_document(
        db_session_factory, memory_providers, USER, kind="text", data=PHRASE.encode()
    )
    await ingest(runtime_down, USER, doc.id)  # aucune exception
    done = await reload(db_session_factory, USER, doc.id)
    assert done.status == "error" and done.item_id is not None
    assert done.error is not None
    assert done.error["code"] in ("embeddings_unavailable", "memory_unavailable")
    assert "indisponible" in done.error["message"]
    async with db_session_factory() as db:
        item = await MemoryItemRepository(db, USER).get(done.item_id)
        chunks = await ChunkRepository(db, USER).for_item(done.item_id)
    assert item is not None and item.indexed_at is None and len(chunks) == 1


class _Boom:
    kind = "text"

    async def extract(self, source: SourceInput, tools: ExtractionTools) -> Extracted:
        raise RuntimeError("chemin secret /x")


async def test_unexpected_exception_message_is_generic(
    runtime: MemoryRuntime,
    db_session_factory: Factory,
    memory_providers: MemoryProviders,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setitem(INGESTION_SOURCES, "text", _Boom())
    doc = await add_document(
        db_session_factory, memory_providers, USER, kind="text", data=b"x", name="secret.txt"
    )
    with caplog.at_level(logging.INFO):
        await ingest(runtime, USER, doc.id)
    done = await reload(db_session_factory, USER, doc.id)
    assert done.error == {
        "code": "ingestion_failed",
        "message": "L'import a échoué de façon inattendue.",
    }
    assert "secret" not in caplog.text and doc.id in caplog.text and "RuntimeError" in caplog.text


async def test_url_errors_become_document_error_and_page_title_names_it(
    runtime: MemoryRuntime,
    db_session_factory: Factory,
    memory_providers: MemoryProviders,
    caplog: pytest.LogCaptureFixture,
) -> None:
    web = memory_providers.web
    assert isinstance(web, FakeWebReader)
    web.pages["https://interne.example/"] = UrlForbidden()
    web.pages["https://example.org/a"] = WebDocument(
        "https://example.org/a", "Bel article", PHRASE, None, None, "fr", None
    )
    bad = await add_document(
        db_session_factory,
        memory_providers,
        USER,
        kind="url",
        url="https://interne.example/",
        name="interne.example",
    )
    good = await add_document(
        db_session_factory,
        memory_providers,
        USER,
        kind="url",
        url="https://example.org/a",
        name="example.org",
    )
    with caplog.at_level(logging.INFO):
        await ingest(runtime, USER, bad.id)
        await ingest(runtime, USER, good.id)
    failed = await reload(db_session_factory, USER, bad.id)
    assert failed.status == "error" and failed.error is not None
    assert failed.error["code"] == "url_forbidden"
    done = await reload(db_session_factory, USER, good.id)
    assert done.status == "indexed" and done.name == "Bel article"
    assert "example" not in caplog.text


class _WriteProbe(HashingEmbedder):
    """Pendant la vectorisation, un autre écrivain prend le verrou d'écriture de SQLite : si la
    chaîne le tenait encore, il attendrait 5 s (`busy_timeout`) puis échouerait."""

    def __init__(self, factory: Factory) -> None:
        super().__init__(FAKE_DIMENSION)
        self.factory = factory
        self.waits: list[float] = []

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        start = time.monotonic()
        async with self.factory() as db:
            await db.execute(update(Document).where(Document.id == "").values(name="x"))
            await db.commit()
        self.waits.append(time.monotonic() - start)
        return await super().aembed_documents(texts)


async def test_worker_embeds_outside_any_write_transaction(
    db_session_factory: Factory, memory_providers: MemoryProviders
) -> None:
    probe = _WriteProbe(db_session_factory)
    index = QdrantMemoryRepository(
        AsyncQdrantClient(location=":memory:"), probe, collection="memory", dimension=FAKE_DIMENSION
    )
    providers = replace(memory_providers, embedder=probe, index=index)
    async with memory_runtime(db_session_factory, providers) as rt:
        doc = await add_document(
            db_session_factory, providers, USER, kind="text", data=PHRASE.encode()
        )
        await ingest(rt, USER, doc.id)
    assert (await reload(db_session_factory, USER, doc.id)).status == "indexed"
    assert len(probe.waits) == 1 and probe.waits[0] < 1.0
