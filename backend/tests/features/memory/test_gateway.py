"""Passerelle mémoire des agents : écriture (auteur, session, raison), acquis, texte d'un document,
recherche ; pannes d'Ollama et de Qdrant."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.tools.memory_port import AgentWrite
from app.core.errors import AppError
from app.core.providers import MemoryProviders
from app.features.memory.repository import MemoryItemRepository, WriteRepository
from app.features.memory.service.gateway import AgentMemoryGateway
from app.features.memory.service.items import MemoryService
from app.features.memory.service.runtime import MemoryRuntime, memory_runtime
from tests.features.memory.doc_support import add_document, add_indexed_document
from tests.features.memory.helpers import with_embeddings_down

Factory = async_sessionmaker[AsyncSession]


@pytest.fixture
def gateway(runtime: MemoryRuntime) -> AgentMemoryGateway:
    return AgentMemoryGateway(runtime)


def _acquis(title: str, **fields: object) -> AgentWrite:
    values = {"kind": "acquis", "title": title, "text": f"{title} : notions.", "reason": "Vu."}
    return AgentWrite(**{**values, **fields})  # type: ignore[arg-type]


async def test_gateway_write_uses_agent_as_author_and_session(
    gateway: AgentMemoryGateway, db_session_factory: Factory
) -> None:
    done = await gateway.write(
        "u1",
        "s1",
        "archivist",
        _acquis("Attention", tags=("nlp",), evidence=("d1",), source_id="d1"),
    )
    assert (done.kind, done.title, done.status, done.created) == (
        "acquis",
        "Attention",
        "active",
        True,
    )
    async with db_session_factory() as db:
        item = await MemoryItemRepository(db, "u1").get(done.item_id)
        writes = await WriteRepository(db, "u1").for_item(done.item_id)
    assert item is not None and item.created_by == "archivist" and item.session_id == "s1"
    assert item.indexed_at is not None and item.source_id == "d1" and item.tags == ["nlp"]
    assert item.meta == {"level": "declare", "evidence": ["d1"], "reason": "Vu."}
    assert [(w.author, w.session_id, w.reason, w.action) for w in writes] == [
        ("archivist", "s1", "Vu.", "create")
    ]


async def test_gateway_write_decision_is_pending_and_not_indexed(
    gateway: AgentMemoryGateway, db_session_factory: Factory
) -> None:
    done = await gateway.write(
        "u1", "s1", "archivist", AgentWrite("decision", "Rust", "On part sur Rust.", "Débat.")
    )
    assert (done.status, done.created) == ("pending", True)
    async with db_session_factory() as db:  # validée malgré l'absence d'indexation
        item = await MemoryItemRepository(db, "u1").get(done.item_id)
    assert item is not None and item.status == "pending" and item.indexed_at is None


async def test_gateway_write_same_content_twice_creates_once(
    gateway: AgentMemoryGateway, db_session_factory: Factory
) -> None:
    first = await gateway.write("u1", "s1", "archivist", _acquis("Attention"))
    again = await gateway.write("u1", "s1", "archivist", _acquis("attention"))
    assert (first.created, again.created, again.item_id) == (True, False, first.item_id)
    async with db_session_factory() as db:
        assert len(await WriteRepository(db, "u1").for_item(first.item_id)) == 1


async def test_gateway_write_without_reason_is_refused(gateway: AgentMemoryGateway) -> None:
    with pytest.raises(AppError) as exc:
        await gateway.write("u1", "s1", "archivist", _acquis("X", reason=" "))
    assert exc.value.code == "memory_reason_required"


async def test_gateway_write_keeps_item_when_embeddings_down(
    db_session_factory: Factory, memory_providers: MemoryProviders
) -> None:
    async with memory_runtime(db_session_factory, with_embeddings_down(memory_providers)) as rt:
        done = await AgentMemoryGateway(rt).write("u1", "s1", "archivist", _acquis("Attention"))
    assert done.created is True
    async with db_session_factory() as db:
        item = await MemoryItemRepository(db, "u1").get(done.item_id)
    assert item is not None and item.indexed_at is None


async def test_gateway_skills_reads_acquis_levels(
    gateway: AgentMemoryGateway, service: MemoryService
) -> None:
    await gateway.write("u1", "s1", "archivist", _acquis("Python"))
    await gateway.write("u1", "s1", "archivist", _acquis("Rust"))
    await gateway.write("u1", "s1", "archivist", _acquis("SQL", level="en_cours"))
    await gateway.write("u1", "s1", "archivist", AgentWrite("lecon", "Autre", "x", "Cours."))
    await gateway.write("u2", "s2", "archivist", _acquis("Go"))
    summary = await gateway.skills("u1")
    assert summary.total == 3 and summary.by_level == {"declare": 2, "en_cours": 1}
    assert sorted(s.title for s in summary.skills) == ["Python", "Rust", "SQL"]
    assert {s.title: s.level for s in summary.skills}["SQL"] == "en_cours"
    assert (await gateway.skills("nobody")).as_text() == "Aucun acquis en mémoire."


async def test_document_text_returns_first_chunks(
    gateway: AgentMemoryGateway,
    db_session_factory: Factory,
    memory_providers: MemoryProviders,
    runtime: MemoryRuntime,
) -> None:
    text = " ".join(f"mot{n}" for n in range(1500))  # plusieurs fragments de 500 tokens
    doc_id = await add_indexed_document(
        db_session_factory, memory_providers, runtime, "u1", text=text
    )
    full = await gateway.document_text("u1", doc_id, max_chunks=50)
    first = await gateway.document_text("u1", doc_id, max_chunks=2)
    assert full is not None and first is not None and len(full.chunks) >= 3
    assert (first.document_id, first.title) == (doc_id, "Cours NLP")
    assert first.chunks == full.chunks[:2] and first.chunks[0].startswith("mot0 ")


async def test_document_text_absent_or_foreign_or_unindexed_is_none(
    gateway: AgentMemoryGateway,
    db_session_factory: Factory,
    memory_providers: MemoryProviders,
    runtime: MemoryRuntime,
) -> None:
    doc_id = await add_indexed_document(
        db_session_factory, memory_providers, runtime, "u1", text="du texte"
    )
    assert await gateway.document_text("u1", "inconnu", max_chunks=2) is None
    assert await gateway.document_text("u2", doc_id, max_chunks=2) is None
    queued = await add_document(
        db_session_factory, memory_providers, "u1", kind="text", name="b.txt", source_hash="autre"
    )
    assert await gateway.document_text("u1", queued.id, max_chunks=2) is None


async def test_gateway_search_returns_views_and_wrapped_agent_text(
    gateway: AgentMemoryGateway,
) -> None:
    await gateway.write("u1", "s1", "archivist", _acquis("Attention"))
    found = await gateway.search("u1", "Attention : notions", kinds=["acquis"], k=8)
    assert [(h.kind, h.title, h.created_by) for h in found.hits] == [
        ("acquis", "Attention", "archivist")
    ]
    assert "<<<CONTENU_NON_FIABLE" in found.agent_text
    assert (await gateway.search("u2", "Attention", kinds=None, k=8)).hits == []
