"""Mémoire et annulation des écritures directes (10.W, relecture) : l'appel n'indexe pas (la ligne
est écrite avec `indexed_at` vide, l'indexation suit, hors de l'appel), l'annulation d'une création
ou d'une retouche remet la mémoire dans son état d'avant (texte, fragments, recherche), et la tâche
d'entretien rattrape un élément resté en attente."""

from types import SimpleNamespace
from typing import cast

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select

from app.db.models.memory import MemoryChunk, MemoryItem, MemoryWrite
from app.features.memory.service import direct as memory_direct
from app.features.memory.service.direct import drain_indexing, index_pending
from app.scheduler.base import JobContext
from app.scheduler.jobs import mcp_housekeeping
from tests.mcp.adapter_support import call
from tests.mcp.support import API, Mcp
from tests.support.direct import Seed, lesson_text

OLD = lesson_text("Les mitochondries produisent l'énergie des cellules vivantes.")
NEW = lesson_text("Les volcans islandais crachent une lave basaltique très fluide.")
FEATURES = ("lessons", "postings")


@pytest.fixture
def paused(monkeypatch: pytest.MonkeyPatch) -> None:
    """L'indexation de fond ne part pas seule : le test la fait passer quand il le décide."""
    monkeypatch.setattr(memory_direct, "_paused", True)


def resume(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(memory_direct, "_paused", False)


async def lesson_item(app: FastAPI) -> MemoryItem:
    async with app.state.session_factory() as db:
        return (await db.execute(select(MemoryItem).where(MemoryItem.kind == "lecon"))).scalar_one()


async def chunk_texts(app: FastAPI, item_id: str) -> list[str]:
    async with app.state.session_factory() as db:
        stmt = select(MemoryChunk.text).where(MemoryChunk.item_id == item_id)
        return list((await db.execute(stmt.order_by(MemoryChunk.ordinal))).scalars())


async def found(client: httpx.AsyncClient, query: str) -> list[str]:
    """Les textes que la recherche de la mémoire rend pour `query`."""
    r = await client.post(f"{API}/memory/search", json={"query": query, "k": 8})
    assert r.status_code == 200, r.text
    return [hit["text"] for hit in r.json()["hits"]]


async def undo_last(claude: Mcp) -> httpx.Response:
    changes = (await claude.http.get(f"{API}/mcp/changes")).json()
    last = next(change for change in changes if change["undone_at"] is None)
    return await claude.http.post(f"{API}/mcp/changes/{last['call_id']}/undo")


async def write(claude: Mcp, token: str, drafted: Seed, markdown: str) -> str:
    made, is_error = await call(
        claude,
        token,
        "lessons_write_lesson",
        {"module_id": drafted.modules[0], "markdown": markdown},
    )
    assert not is_error, made
    return str(made["data"]["id"])


async def test_write_leaves_the_item_unindexed_until_the_background_pass(
    client: httpx.AsyncClient, app: FastAPI, drafted: Seed, claude: Mcp, paused: None
) -> None:
    token = await claude.token(FEATURES, "write")
    await write(claude, token, drafted, OLD)

    item = await lesson_item(app)
    assert item.indexed_at is None and await chunk_texts(app, item.id) == []
    assert item.created_by == "claude"

    assert await index_pending(app.state.memory, drafted.user_id) == 1

    indexed = await lesson_item(app)
    assert indexed.indexed_at is not None and await chunk_texts(app, item.id) != []
    assert any("mitochondries" in text for text in await found(client, "mitochondries cellules"))


async def test_patch_then_undo_restores_text_fragments_and_search(
    client: httpx.AsyncClient,
    app: FastAPI,
    drafted: Seed,
    claude: Mcp,
    paused: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = await claude.token(FEATURES, "write")
    lesson_id = await write(claude, token, drafted, OLD)
    await index_pending(app.state.memory, drafted.user_id)
    before = await lesson_item(app)

    patched, is_error = await call(
        claude, token, "lessons_update_lesson", {"lesson_id": lesson_id, "markdown": NEW}
    )
    assert not is_error, patched

    mid = await lesson_item(
        app
    )  # retouchée sans réindexer dans l'appel : les anciens fragments restent
    assert mid.text == NEW.strip() and mid.indexed_at is None
    assert any("mitochondries" in text for text in await chunk_texts(app, mid.id))
    async with app.state.session_factory() as db:
        authors = (await db.execute(select(MemoryWrite.author, MemoryWrite.action))).all()
    assert ("claude", "update") in [(a, b) for a, b in authors]

    await index_pending(
        app.state.memory, drafted.user_id
    )  # passée entre la retouche et l'annulation
    assert any("volcans" in text for text in await found(client, "volcans lave"))
    resume(monkeypatch)

    undone = await undo_last(claude)

    assert undone.status_code == 200, undone.text
    restored = await lesson_item(app)
    assert restored.text == before.text and restored.title == before.title
    assert (
        restored.indexed_at is None
    )  # à réindexer : les fragments sont encore ceux du nouveau texte
    await drain_indexing()  # l'annulation lance elle-même la réindexation
    assert (await lesson_item(app)).indexed_at is not None
    assert any("mitochondries" in text for text in await chunk_texts(app, before.id))
    assert not any("volcans" in text for text in await chunk_texts(app, before.id))
    assert any("mitochondries" in text for text in await found(client, "mitochondries cellules"))
    assert not any("volcans" in text for text in await found(client, "volcans lave"))


async def test_created_then_undone_item_is_gone_even_after_indexing(
    client: httpx.AsyncClient,
    app: FastAPI,
    drafted: Seed,
    claude: Mcp,
    paused: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = await claude.token(FEATURES, "write")
    await write(claude, token, drafted, OLD)
    item = await lesson_item(app)
    await index_pending(app.state.memory, drafted.user_id)  # fragments et vecteurs existent
    assert await found(client, "mitochondries cellules")
    resume(monkeypatch)

    undone = await undo_last(claude)

    assert undone.status_code == 200, undone.text
    async with app.state.session_factory() as db:
        assert (await db.execute(select(MemoryItem))).scalars().all() == []
        assert (await db.execute(select(MemoryChunk))).scalars().all() == []
    assert await found(client, "mitochondries cellules") == []  # le vecteur orphelin est écarté
    await drain_indexing()
    assert item.id  # l'élément n'existe plus nulle part


async def test_housekeeping_indexes_items_left_pending(
    client: httpx.AsyncClient, app: FastAPI, drafted: Seed, claude: Mcp
) -> None:
    token = await claude.token(FEATURES, "write")
    await write(claude, token, drafted, OLD)
    await drain_indexing()
    async with app.state.session_factory() as db:
        item = (await db.execute(select(MemoryItem))).scalar_one()
        item.indexed_at = None  # l'application a redémarré avant la tâche d'indexation
        await db.commit()
    memory = SimpleNamespace(memory=app.state.memory)
    context = cast(
        JobContext,
        SimpleNamespace(
            session_factory=app.state.session_factory, daily=SimpleNamespace(projects=memory)
        ),
    )

    await mcp_housekeeping.run(context)

    assert (await lesson_item(app)).indexed_at is not None
