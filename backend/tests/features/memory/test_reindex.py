"""Réindexation (4.6, D67) : job du worker, état en mémoire, un seul job à la fois, écritures
concurrentes rattrapées, panne lisible. Aucun réseau : `HashingEmbedder` et Qdrant `:memory:`."""

import asyncio
from collections.abc import AsyncIterator
from dataclasses import replace
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.providers import MemoryProviders
from app.features.memory.repository import ChunkRepository, MemoryItemRepository
from app.features.memory.schemas import MemoryItemPatch, ReindexState
from app.features.memory.service import jobs as jobs_module
from app.features.memory.service import reindex as reindex_module
from app.features.memory.service.items import MemoryService
from app.features.memory.service.runtime import MemoryRuntime, memory_runtime
from app.providers.embeddings.fake import HashingEmbedder
from app.providers.vector.qdrant import QdrantMemoryRepository
from tests.features.memory.helpers import draft, with_embeddings_down
from tests.support.memory import FAKE_DIMENSION

USER = "u1"
SEARCH = "/api/v1/memory/search"
Factory = async_sessionmaker[AsyncSession]


class _Gate(HashingEmbedder):
    """Une fois armée, la prochaine vectorisation de documents attend `release`."""

    def __init__(self) -> None:
        super().__init__(FAKE_DIMENSION)
        self.entered, self.release = asyncio.Event(), asyncio.Event()
        self._armed = False

    def arm(self) -> None:
        self._armed, self.entered, self.release = True, asyncio.Event(), asyncio.Event()

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        if self._armed:
            self._armed = False
            self.entered.set()
            await self.release.wait()
        return await super().aembed_documents(texts)


@pytest.fixture
def gate() -> _Gate:
    return _Gate()


@pytest.fixture
async def rt(
    db_session_factory: Factory, memory_providers: MemoryProviders, gate: _Gate
) -> AsyncIterator[MemoryRuntime]:
    index = QdrantMemoryRepository(
        AsyncQdrantClient(location=":memory:"), gate, collection="memory", dimension=64
    )
    providers = replace(memory_providers, embedder=gate, index=index)
    async with memory_runtime(db_session_factory, providers) as runtime:
        yield runtime


async def _write(rt: MemoryRuntime, factory: Factory, **fields: Any) -> str:
    async with factory() as db:
        item = (await MemoryService(db, USER, rt).write(draft(**fields))).item
        await db.commit()
        return item.id


async def _vectors(rt: MemoryRuntime, item_id: str | None = None) -> int:
    records = await rt.providers.index.vectors(USER, limit=10_000)
    return sum(1 for r in records if item_id is None or r.payload.item_id == item_id)


async def _consistent(rt: MemoryRuntime, factory: Factory, item_id: str) -> None:
    """L'élément est indexé et ses vecteurs sont exactement ses fragments en base."""
    async with factory() as db:
        item = await MemoryItemRepository(db, USER).get(item_id)
        chunks = await ChunkRepository(db, USER).for_item(item_id)
    assert item is not None and item.indexed_at is not None
    records = await rt.providers.index.vectors(USER, limit=10_000)
    assert {r.chunk_id for r in records if r.payload.item_id == item_id} == {c.id for c in chunks}


async def test_reindex_rebuilds_vectors_from_text(app: FastAPI, client: httpx.AsyncClient) -> None:
    texts = ["Je sais écrire des scripts Python.", "Poste à Lyon.", "Viser le Rust."]
    for i, text in enumerate(texts):
        r = await client.post(
            "/api/v1/memory/items", json={"kind": "offre", "title": f"T{i}", "text": text}
        )
        assert r.status_code == 201
    n = len(texts)
    runtime: MemoryRuntime = app.state.memory
    user = app.state.local_user_id
    await runtime.providers.index.delete_user(user)  # vecteurs effacés à la main
    assert (await client.post(SEARCH, json={"query": "Python"})).json()["hits"] == []

    r = await client.post("/api/v1/memory/reindex")
    assert r.status_code == 202
    assert r.json() == {"status": "queued", "done": 0, "total": 0, "error": None}
    await runtime.jobs.join()

    hits = (await client.post(SEARCH, json={"query": "Python"})).json()["hits"]
    assert [h["title"] for h in hits][:1] == ["T0"]
    stats = (await client.get("/api/v1/memory/stats")).json()
    assert stats["reindex"] == {"status": "done", "done": n, "total": n, "error": None}
    assert stats["unindexed_items"] == 0 and stats["total_chunks"] == n


async def test_reindex_twice_returns_current_state_without_second_job(
    rt: MemoryRuntime, db_session_factory: Factory, gate: _Gate, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _write(rt, db_session_factory, title="A", text="Premier texte.")
    runs: list[str] = []
    real = jobs_module.reindex_user

    async def counted(runtime: MemoryRuntime, user_id: str, report: Any) -> None:
        runs.append(user_id)
        await real(runtime, user_id, report)

    monkeypatch.setattr(jobs_module, "reindex_user", counted)
    gate.arm()
    first = rt.jobs.enqueue_reindex(USER)
    assert first.status == "queued"
    assert rt.jobs.enqueue_reindex(USER) == first  # encore en file : même état
    await asyncio.wait_for(gate.entered.wait(), 3)
    running = rt.jobs.enqueue_reindex(USER)
    assert running.status == "running" and running == rt.jobs.reindex_state(USER)
    gate.release.set()
    await rt.jobs.join()
    assert runs == [USER]
    assert rt.jobs.reindex_state(USER) == ReindexState(status="done", done=1, total=1, error=None)
    assert rt.jobs.reindex_state("autre").status == "idle"  # par utilisateur
    again = rt.jobs.enqueue_reindex(USER)  # fini : un nouveau job est possible
    assert again.status == "queued"
    await rt.jobs.join()
    assert runs == [USER, USER]


async def test_write_during_reindex_is_indexed_by_the_reindex_loop(
    rt: MemoryRuntime, db_session_factory: Factory, gate: _Gate
) -> None:
    await _write(rt, db_session_factory, title="A", text="Premier texte.")
    gate.arm()
    rt.jobs.enqueue_reindex(USER)
    await asyncio.wait_for(gate.entered.wait(), 3)  # 1er lot bloqué dans l'embedder
    # Une écriture d'agent arrive : elle n'attend ni le verrou ni l'embedder.
    item_id = await asyncio.wait_for(
        _write(rt, db_session_factory, title="B", text="Écrit pendant la réindexation."), 2
    )
    assert await _vectors(rt, item_id) == 0
    gate.release.set()
    await rt.jobs.join()
    async with db_session_factory() as db:
        item = await MemoryItemRepository(db, USER).get(item_id)
    assert item is not None and item.indexed_at is not None
    assert await _vectors(rt, item_id) == 1
    assert rt.jobs.reindex_state(USER) == ReindexState(status="done", done=2, total=2, error=None)
    assert not rt.indexer.reindexing(USER)


async def test_update_during_reindex_never_keeps_stale_vectors(
    rt: MemoryRuntime, db_session_factory: Factory, gate: _Gate
) -> None:
    item_id = await _write(rt, db_session_factory, title="A", text="Ancien texte.")
    gone_id = await _write(rt, db_session_factory, title="G", text="Bientôt supprimé.")
    gate.arm()
    rt.jobs.enqueue_reindex(USER)
    await asyncio.wait_for(gate.entered.wait(), 3)  # fragments du lot préparés, push bloqué
    async with db_session_factory() as db:
        service = MemoryService(db, USER, rt)
        await service.update(item_id, MemoryItemPatch(text="Nouveau texte réécrit."))
        await service.delete(gone_id)
        await db.commit()
    gate.release.set()
    await rt.jobs.join()
    await _consistent(rt, db_session_factory, item_id)
    assert await _vectors(rt, gone_id) == 0  # aucun vecteur orphelin de l'élément supprimé
    assert rt.jobs.reindex_state(USER).status == "done"


async def test_writer_in_flight_when_reindex_starts_is_not_lost(
    rt: MemoryRuntime, db_session_factory: Factory, gate: _Gate
) -> None:
    gate.arm()
    writer = asyncio.create_task(_write(rt, db_session_factory, title="W", text="En vol."))
    await asyncio.wait_for(gate.entered.wait(), 3)  # l'écrivain est dans `push`
    rt.jobs.enqueue_reindex(USER)
    await asyncio.sleep(0.05)
    assert rt.jobs.reindex_state(USER).status == "running"
    gate.release.set()
    item_id = await asyncio.wait_for(writer, 3)
    await rt.jobs.join()
    await _consistent(rt, db_session_factory, item_id)
    assert await _vectors(rt) == 1


async def test_write_finishing_after_the_last_read_is_not_left_behind(
    rt: MemoryRuntime, db_session_factory: Factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Un écrivain qui valide son élément juste après la lecture du lot vide : la boucle le voit
    (génération des écrivains changée) et relit au lieu de finir."""
    await _write(rt, db_session_factory, title="A", text="Premier texte.")
    real = reindex_module._batch
    late: list[str] = []

    async def batch_then_late_write(runtime: MemoryRuntime, user_id: str) -> tuple[int, int]:
        result = await real(runtime, user_id)
        if result[1] == 0 and not late:
            late.append(await _write(rt, db_session_factory, title="L", text="Arrivé tard."))
        return result

    monkeypatch.setattr(reindex_module, "_batch", batch_then_late_write)
    rt.jobs.enqueue_reindex(USER)
    await rt.jobs.join()
    await _consistent(rt, db_session_factory, late[0])
    assert rt.jobs.reindex_state(USER) == ReindexState(status="done", done=2, total=2, error=None)


async def test_reindex_failure_reports_readable_error(
    db_session_factory: Factory, memory_providers: MemoryProviders
) -> None:
    down = with_embeddings_down(memory_providers)
    async with memory_runtime(db_session_factory, down) as runtime:
        await _write(runtime, db_session_factory, title="A", text="Premier texte.")
        runtime.jobs.enqueue_reindex(USER)
        await runtime.jobs.join()
        state = runtime.jobs.reindex_state(USER)
        assert state.status == "failed" and state.total == 1 and state.done == 0
        assert state.error is not None
        assert state.error.startswith("Le service d'embeddings (Ollama)")
        assert not runtime.indexer.reindexing(USER)
        async with db_session_factory() as db:
            assert await MemoryItemRepository(db, USER).count_unindexed() == 1  # gardé, à rattraper


async def test_unexpected_reindex_error_is_generic(
    rt: MemoryRuntime, db_session_factory: Factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def boom(*_: Any) -> None:
        raise RuntimeError("chemin/secret")

    monkeypatch.setattr(jobs_module, "reindex_user", boom)
    rt.jobs.enqueue_reindex(USER)
    await rt.jobs.join()
    state = rt.jobs.reindex_state(USER)
    assert state.status == "failed"
    assert state.error == "La réindexation a échoué de façon inattendue."
