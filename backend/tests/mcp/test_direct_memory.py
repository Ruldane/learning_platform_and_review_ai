"""La leçon n'entre en mémoire qu'après vérification, puis l'indexation suit en tâche de fond."""

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
from tests.support.direct import Seed
from tests.support.lesson_verification import submission_text, wait_session

OLD = submission_text(
    "Module Bases", "Les mitochondries produisent l'énergie des cellules vivantes."
)
NEW = submission_text(
    "Module Bases", "Les volcans islandais crachent une lave basaltique très fluide."
)
FEATURES = ("lessons", "postings")
pytestmark = pytest.mark.usefixtures("accept_lesson", "settled_indexing")


@pytest.fixture
def paused(monkeypatch: pytest.MonkeyPatch) -> None:
    """L'indexation de fond ne part pas seule : le test la fait passer quand il le décide."""
    monkeypatch.setattr(memory_direct, "_paused", True)


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


async def write(
    client: httpx.AsyncClient, claude: Mcp, token: str, drafted: Seed, markdown: str
) -> str:
    made, is_error = await call(
        claude,
        token,
        "lessons_write_lesson",
        {"module_id": drafted.modules[0], "markdown": markdown},
    )
    assert not is_error, made
    assert (await wait_session(client, made["data"]["verification_session_id"]))[
        "status"
    ] == "completed"
    return str(made["data"]["id"])


async def test_write_leaves_the_item_unindexed_until_the_background_pass(
    client: httpx.AsyncClient, app: FastAPI, drafted: Seed, claude: Mcp, paused: None
) -> None:
    token = await claude.token(FEATURES, "write")
    await write(client, claude, token, drafted, OLD)

    item = await lesson_item(app)
    assert item.indexed_at is None and await chunk_texts(app, item.id) == []
    assert item.created_by == "claude"

    assert await index_pending(app.state.memory, drafted.user_id) == 1

    indexed = await lesson_item(app)
    assert indexed.indexed_at is not None and await chunk_texts(app, item.id) != []
    assert any("mitochondries" in text for text in await found(client, "mitochondries cellules"))


async def test_verified_patch_replaces_text_then_refreshes_search(
    client: httpx.AsyncClient,
    app: FastAPI,
    drafted: Seed,
    claude: Mcp,
    paused: None,
) -> None:
    token = await claude.token(FEATURES, "write")
    lesson_id = await write(client, claude, token, drafted, OLD)
    await index_pending(app.state.memory, drafted.user_id)
    before = await lesson_item(app)

    patched, is_error = await call(
        claude, token, "lessons_update_lesson", {"lesson_id": lesson_id, "markdown": NEW}
    )
    assert not is_error, patched
    assert (await wait_session(client, patched["data"]["verification_session_id"]))[
        "status"
    ] == "completed"

    mid = await lesson_item(app)
    assert mid.id == before.id and mid.text == NEW.strip() and mid.indexed_at is None
    assert any("mitochondries" in text for text in await chunk_texts(app, mid.id))
    async with app.state.session_factory() as db:
        authors = (await db.execute(select(MemoryWrite.author, MemoryWrite.action))).all()
    assert ("claude", "update") in [(a, b) for a, b in authors]

    await index_pending(app.state.memory, drafted.user_id)
    assert any("volcans" in text for text in await found(client, "volcans lave"))
    assert not any(
        "mitochondries" in text for text in await found(client, "mitochondries cellules")
    )


async def test_housekeeping_indexes_items_left_pending(
    client: httpx.AsyncClient, app: FastAPI, drafted: Seed, claude: Mcp
) -> None:
    token = await claude.token(FEATURES, "write")
    await write(client, claude, token, drafted, OLD)
    await drain_indexing()
    async with app.state.session_factory() as db:
        item = (await db.execute(select(MemoryItem).where(MemoryItem.kind == "lecon"))).scalar_one()
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
