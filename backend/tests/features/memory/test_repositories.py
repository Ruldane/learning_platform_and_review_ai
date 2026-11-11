from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.memory import Document, MemoryChunk
from app.features.memory.repository import (
    ChunkRepository,
    DocumentRepository,
    ItemFilter,
    MemoryItemRepository,
    WriteRepository,
    list_documents_to_resume,
)
from app.features.memory.service.text import ChunkDraft
from tests.features.memory.conftest import MakeItem

T0 = datetime(2026, 1, 1, tzinfo=UTC)


async def _doc(db: AsyncSession, user_id: str, source_hash: str, **fields: Any) -> Document:
    values: dict[str, Any] = {
        "name": "cv.pdf",
        "source_kind": "pdf",
        "source_hash": source_hash,
        **fields,
    }
    return await DocumentRepository(db, user_id).add(**values)


async def test_unique_source_hash_per_user(db: AsyncSession) -> None:
    doc = await _doc(db, "u1", "h1")
    assert doc.status == "queued" and doc.learned is False and doc.error is None
    await _doc(db, "u2", "h1")  # un autre utilisateur peut importer le même fichier
    with pytest.raises(IntegrityError):
        await _doc(db, "u1", "h1")


async def test_unique_content_hash_per_user(db: AsyncSession, make_item: MakeItem) -> None:
    item = await make_item("u1", title="a", content_hash="same")
    assert item.status == "active" and item.tags == [] and item.meta == {}
    assert item.indexed_at is None
    await make_item("u2", title="a", content_hash="same")
    with pytest.raises(IntegrityError):
        await make_item("u1", title="b", content_hash="same")


async def test_find_by_source_hash_is_user_scoped(db: AsyncSession) -> None:
    doc = await _doc(db, "u1", "h1")
    assert (await DocumentRepository(db, "u1").find_by_source_hash("h1")) == doc
    assert await DocumentRepository(db, "u2").find_by_source_hash("h1") is None
    assert await DocumentRepository(db, "u1").find_by_source_hash("absent") is None


async def test_find_by_hash_is_user_scoped(db: AsyncSession, make_item: MakeItem) -> None:
    item = await make_item("u1", content_hash="x")
    assert await MemoryItemRepository(db, "u1").find_by_hash("x") == item
    assert await MemoryItemRepository(db, "u2").find_by_hash("x") is None


async def test_documents_recent_and_for_item(db: AsyncSession, make_item: MakeItem) -> None:
    item = await make_item("u1")
    old = await _doc(db, "u1", "a", created_at=T0)
    new = await _doc(db, "u1", "b", created_at=T0 + timedelta(days=1), item_id=item.id)
    await _doc(db, "u2", "c")
    repo = DocumentRepository(db, "u1")
    assert [d.id for d in await repo.list_recent()] == [new.id, old.id]
    assert [d.id for d in await repo.list_recent(limit=1)] == [new.id]
    assert [d.id for d in await repo.for_item(item.id)] == [new.id]
    assert await DocumentRepository(db, "u2").for_item(item.id) == []


async def test_filtered_by_kind_tag_author_dates(db: AsyncSession, make_item: MakeItem) -> None:
    day = timedelta(days=1)
    a = await make_item(title="a", kind="acquis", tags=["python", "web"], created_at=T0)
    b = await make_item(title="b", tags=["python"], created_by="agent", created_at=T0 + day)
    c = await make_item(title="c", tags=[], created_at=T0 + 2 * day)
    d = await make_item(title="d", tags=["python"], status="pending")
    await make_item("u2", title="e", tags=["python"])
    repo = MemoryItemRepository(db, "u1")

    async def ids(f: ItemFilter, limit: int = 50, offset: int = 0) -> tuple[list[str], int]:
        items, total = await repo.filtered(f, limit=limit, offset=offset)
        return [i.id for i in items], total

    assert await ids(ItemFilter()) == ([c.id, b.id, a.id], 3)  # récents d'abord, actifs seulement
    assert await ids(ItemFilter(kind="acquis")) == ([a.id], 1)
    assert await ids(ItemFilter(tag="python")) == ([b.id, a.id], 2)
    assert await ids(ItemFilter(tag="pyth")) == ([], 0)  # étiquette exacte, pas une sous-chaîne
    assert await ids(ItemFilter(author="agent")) == ([b.id], 1)
    assert await ids(ItemFilter(since=T0 + day)) == ([c.id, b.id], 2)
    assert await ids(ItemFilter(until=T0 + day)) == ([b.id, a.id], 2)
    assert await ids(ItemFilter(status="pending")) == ([d.id], 1)
    assert await ids(ItemFilter(), limit=1, offset=1) == ([b.id], 3)  # total sans limite


async def test_item_counts_and_batches(db: AsyncSession, make_item: MakeItem) -> None:
    day = timedelta(days=1)
    a = await make_item(title="a", kind="acquis", indexed_at=datetime.now(UTC), created_at=T0)
    b = await make_item(title="b", created_at=T0 + day)
    c = await make_item(title="c", created_at=T0 + 2 * day)
    await make_item(title="d", kind="decision", status="pending")
    await make_item("u2", title="x")
    repo = MemoryItemRepository(db, "u1")
    assert await repo.count_by_kind() == {"acquis": 1, "lecon": 2}
    assert await repo.count_by_kind("pending") == {"decision": 1}
    assert await repo.count_status("active") == 3 and await repo.count_status("pending") == 1
    assert await repo.count_unindexed() == 2
    assert [i.id for i in await repo.unindexed_batch(1)] == [b.id]
    assert [i.id for i in await repo.active()] == [c.id, b.id, a.id]
    assert [i.id for i in await repo.active(limit=2)] == [c.id, b.id]
    assert set(await repo.get_many([a.id, c.id, "absent"])) == {a.id, c.id}
    assert await repo.get_many([]) == {}
    assert await MemoryItemRepository(db, "u2").get_many([a.id]) == {}
    await repo.clear_indexed()
    assert await repo.count_unindexed() == 3
    assert await MemoryItemRepository(db, "u2").count_unindexed() == 1


async def test_clear_indexed_only_touches_the_user(db: AsyncSession, make_item: MakeItem) -> None:
    mine = await make_item("u1", indexed_at=datetime.now(UTC))
    theirs = await make_item("u2", title="z", indexed_at=datetime.now(UTC))
    await MemoryItemRepository(db, "u1").clear_indexed()
    await db.refresh(mine)
    await db.refresh(theirs)
    assert mine.indexed_at is None and theirs.indexed_at is not None


async def test_replace_chunks_for_item(db: AsyncSession, make_item: MakeItem) -> None:
    item = await make_item()
    repo = ChunkRepository(db, "u1")
    first = await repo.replace_for_item(
        item.id, [ChunkDraft(0, "un", 1), ChunkDraft(1, "deux", 1), ChunkDraft(2, "trois", 1)]
    )
    assert [c.ordinal for c in first] == [0, 1, 2] and all(len(c.id) == 36 for c in first)
    second = await repo.replace_for_item(item.id, [ChunkDraft(0, "seul", 1)])
    assert [(c.ordinal, c.text) for c in await repo.for_item(item.id)] == [(0, "seul")]
    assert await repo.count() == 1
    assert set(await repo.get_many([first[0].id, second[0].id])) == {second[0].id}
    assert await ChunkRepository(db, "u2").count() == 0
    assert await repo.replace_for_item(item.id, []) == [] and await repo.count() == 0


async def test_chunks_are_ordered_by_ordinal(db: AsyncSession, make_item: MakeItem) -> None:
    item = await make_item()
    repo = ChunkRepository(db, "u1")
    await repo.replace_for_item(item.id, [ChunkDraft(1, "b", 1), ChunkDraft(0, "a", 1)])
    assert [c.text for c in await repo.for_item(item.id)] == ["a", "b"]


async def test_delete_item_cascades_chunks_and_unlinks_document(
    db: AsyncSession, make_item: MakeItem
) -> None:
    item = await make_item()
    await ChunkRepository(db, "u1").replace_for_item(item.id, [ChunkDraft(0, "a", 1)])
    doc = await _doc(db, "u1", "h", item_id=item.id)
    assert await MemoryItemRepository(db, "u1").delete(item.id) is True
    await db.refresh(doc)
    assert doc.item_id is None
    assert (await db.execute(select(MemoryChunk))).scalars().all() == []


async def test_writes_keep_title_after_item_deletion(db: AsyncSession, make_item: MakeItem) -> None:
    item = await make_item(title="Python", kind="acquis")
    writes = WriteRepository(db, "u1")
    assert await writes.last() is None
    created = await writes.log(
        item=item, action="create", author="agent", session_id="s1", reason="vu en entretien"
    )
    assert (created.item_id, created.item_title, created.kind) == (item.id, "Python", "acquis")
    await MemoryItemRepository(db, "u1").delete(item.id)
    deleted = await writes.log(
        item=item, action="delete", author="user", session_id=None, reason=None
    )
    assert [w.id for w in await writes.for_item(item.id)] == [deleted.id, created.id]
    assert (await writes.last()) == deleted
    assert {w.id for w in await writes.all()} == {created.id, deleted.id}
    assert await WriteRepository(db, "u2").last() is None
    assert await WriteRepository(db, "u2").for_item(item.id) == []


async def test_list_documents_to_resume_all_users_queued_and_processing(db: AsyncSession) -> None:
    second = await _doc(db, "u2", "b", status="processing", created_at=T0 + timedelta(hours=1))
    first = await _doc(db, "u1", "a", status="queued", created_at=T0)
    await _doc(db, "u1", "c", status="indexed")
    await _doc(db, "u1", "d", status="error")
    assert await list_documents_to_resume(db) == [("u1", first.id), ("u2", second.id)]
