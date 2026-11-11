"""Écriture, indexation, mise à jour et suppression des éléments de la mémoire."""

import asyncio
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import AppError
from app.db.models.memory import MemoryChunk, MemoryItem, MemoryWrite
from app.features.memory.schemas import MemoryItemCreate, MemoryItemPatch, SearchRequest
from app.features.memory.service.items import ItemFilter, MemoryService
from app.features.memory.service.runtime import MemoryRuntime
from app.features.memory.service.search import search
from tests.features.memory.helpers import draft

ALL = ItemFilter()


async def _writes(db: AsyncSession, user_id: str = "u1") -> list[MemoryWrite]:
    stmt = (
        select(MemoryWrite)
        .where(MemoryWrite.user_id == user_id)
        .order_by(MemoryWrite.created_at, MemoryWrite.id)
    )
    return list((await db.execute(stmt)).scalars())


async def _count(db: AsyncSession, model: Any) -> int:
    return int((await db.execute(select(func.count()).select_from(model))).scalar_one())


async def _hits(db: AsyncSession, runtime: MemoryRuntime, query: str, user: str = "u1") -> int:
    return len((await search(db, user, runtime, SearchRequest(query=query))).hits)


async def test_write_creates_item_chunks_vectors_and_journal(
    service: MemoryService, db: AsyncSession, runtime: MemoryRuntime
) -> None:
    out = await service.write(
        draft(kind="lecon", author="writer", reason="Leçon 1 publiée.", session_id="s1")
    )
    assert out.created and out.item.indexed_at is not None and out.item.status == "active"
    writes = await _writes(db)
    assert [(w.action, w.author, w.session_id, w.reason) for w in writes] == [
        ("create", "writer", "s1", "Leçon 1 publiée.")
    ]
    assert writes[0].item_id == out.item.id and writes[0].item_title == "Attention"
    assert await _count(db, MemoryChunk) == 1
    assert out.item.meta == {"reason": "Leçon 1 publiée."}
    assert await _hits(db, runtime, "attention mots phrase") == 1


async def test_agent_write_is_idempotent_on_same_content(
    service: MemoryService, db: AsyncSession
) -> None:
    first = await service.write(draft(author="writer"))
    same = draft(author="writer", text="L'attention  pondère les MOTS d'une phrase.")
    again = await service.write(same)
    assert first.created and not again.created and again.item.id == first.item.id
    assert await _count(db, MemoryItem) == 1
    assert len(await _writes(db)) == 1 and await _count(db, MemoryChunk) == 1


async def test_acquis_is_deduplicated_by_title(service: MemoryService, db: AsyncSession) -> None:
    first = await service.write(draft(kind="acquis", author="archivist", title="Python"))
    again = await service.write(
        draft(kind="acquis", author="archivist", title=" python ", text="Autre texte.")
    )
    assert not again.created and again.item.id == first.item.id
    assert await _count(db, MemoryItem) == 1


async def test_concurrent_identical_writes_create_one_item(
    runtime: MemoryRuntime, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    async def write_once() -> bool:
        async with db_session_factory() as session:
            outcome = await MemoryService(session, "u1", runtime).write(draft(author="writer"))
            await session.commit()
            return outcome.created

    created = await asyncio.gather(write_once(), write_once())
    assert sorted(created) == [False, True]
    async with db_session_factory() as session:
        assert await _count(session, MemoryItem) == 1
        assert len(await _writes(session)) == 1
        assert await _count(session, MemoryChunk) == 1


async def test_write_is_atomic_with_the_session_transaction(
    service: MemoryService, db: AsyncSession
) -> None:
    # Sans indexation : `index_item` valide la transaction avant de vectoriser (D66).
    await service.write(draft(author="writer"), index=False)
    await db.rollback()  # l'insertion sous SAVEPOINT ne doit pas valider seule la transaction
    assert await _count(db, MemoryItem) == 0 and await _count(db, MemoryWrite) == 0


async def test_pending_decision_not_indexed_until_confirmed(
    service: MemoryService, db: AsyncSession, runtime: MemoryRuntime
) -> None:
    out = await service.write(
        draft(kind="decision", author="archivist", title="Choix", text="Viser Paris.")
    )
    assert out.created and out.item.status == "pending" and out.item.indexed_at is None
    assert await _hits(db, runtime, "viser paris") == 0
    assert (await service.list_items(ALL, limit=50, offset=0)).total == 0  # pas la liste ordinaire
    pending = await service.list_items(ItemFilter(status="pending"), limit=50, offset=0)
    assert pending.total == 1

    confirmed = await service.update(out.item.id, MemoryItemPatch(status="active"))
    assert confirmed.status == "active" and confirmed.indexed
    assert await _hits(db, runtime, "viser paris") == 1
    writes = await _writes(db)
    assert [w.action for w in writes] == ["create", "confirm"] and writes[1].author == "user"
    again = await service.update(out.item.id, MemoryItemPatch(status="active"))  # déjà actif
    assert again.status == "active" and len(await _writes(db)) == 2


async def test_reject_pending_deletes_and_logs_reject(
    service: MemoryService, db: AsyncSession
) -> None:
    out = await service.write(draft(kind="decision", author="archivist"))
    await service.delete(out.item.id)
    assert await _count(db, MemoryItem) == 0
    assert [(w.action, w.author, w.item_id) for w in await _writes(db)] == [
        ("create", "archivist", out.item.id),
        ("reject", "user", out.item.id),
    ]


async def test_delete_active_removes_chunks_and_vectors_and_logs_delete(
    service: MemoryService, db: AsyncSession, runtime: MemoryRuntime
) -> None:
    out = await service.write(draft(author="writer"))
    await service.delete(out.item.id)
    assert await _count(db, MemoryChunk) == 0 and await _hits(db, runtime, "attention") == 0
    assert [w.action for w in await _writes(db)] == ["create", "delete"]
    assert len(await runtime.providers.index.vectors("u1", limit=10)) == 0
    with pytest.raises(AppError) as raised:
        await service.delete(out.item.id)
    assert raised.value.code == "memory_item_not_found" and raised.value.status_code == 404


async def test_write_keeps_item_when_embeddings_down(
    service_down: MemoryService, db: AsyncSession
) -> None:
    out = await service_down.write(draft(author="writer"))
    assert out.created and out.item.indexed_at is None
    assert await _count(db, MemoryItem) == 1 and await _count(db, MemoryChunk) == 1
    detail = await service_down.detail(out.item.id)
    assert detail.indexed is False and detail.neighbors == []
    created = await service_down.create_by_user(
        MemoryItemCreate(kind="offre", title="Offre", text="Poste de développeur.")
    )
    assert created.indexed is False


async def test_update_text_reindexes_and_logs_update(
    service: MemoryService, db: AsyncSession, runtime: MemoryRuntime
) -> None:
    out = await service.write(draft(author="writer"))
    old_chunk = (await db.execute(select(MemoryChunk.id))).scalar_one()
    patch = MemoryItemPatch(text="Les transformers utilisent des têtes d'attention.")
    updated = await service.update(out.item.id, patch)
    assert updated.text.startswith("Les transformers") and updated.indexed
    writes = await _writes(db)
    assert [w.action for w in writes] == ["create", "update"] and writes[1].author == "user"
    assert await _hits(db, runtime, "transformers têtes") == 1
    ids = [r.chunk_id for r in await runtime.providers.index.vectors("u1", limit=10)]
    assert len(ids) == 1 and ids[0] != old_chunk  # l'ancien point a disparu
    assert (await db.execute(select(MemoryChunk.id))).scalar_one() == ids[0]


async def test_update_title_and_tags_refreshes_the_index_payload(
    service: MemoryService, runtime: MemoryRuntime
) -> None:
    out = await service.write(draft(author="writer"))
    patch = MemoryItemPatch(title="Nouveau titre", tags=["ia", "ia", " nlp "])
    await service.update(out.item.id, patch)
    (record,) = await runtime.providers.index.vectors("u1", limit=10)
    assert record.payload.title == "Nouveau titre" and record.payload.tags == ["ia", "nlp"]


async def test_update_to_existing_content_conflicts(
    service: MemoryService, db: AsyncSession
) -> None:
    await service.write(draft(author="writer", title="A", text="Premier texte."))
    other = await service.write(draft(author="writer", title="B", text="Second texte."))
    with pytest.raises(AppError) as raised:
        await service.update(other.item.id, MemoryItemPatch(text="premier  TEXTE."))
    assert raised.value.status_code == 409 and raised.value.code == "memory_duplicate"
    assert [w.action for w in await _writes(db)] == ["create", "create"]


async def test_update_level_only_for_an_acquis(service: MemoryService, db: AsyncSession) -> None:
    lecon = await service.write(draft(author="writer"))
    with pytest.raises(AppError) as raised:
        await service.update(lecon.item.id, MemoryItemPatch(level="en_cours"))
    assert raised.value.code == "memory_level_forbidden"
    acquis = await service.create_by_user(
        MemoryItemCreate(kind="acquis", title="SQL", text="Jointures et index.")
    )
    assert acquis.level == "declare"
    assert (await service.update(acquis.id, MemoryItemPatch(level="en_cours"))).level == "en_cours"
    assert [w.action for w in await _writes(db)][-1] == "update"


async def test_update_rejects_blank_content(service: MemoryService) -> None:
    out = await service.write(draft(author="writer"))
    with pytest.raises(AppError) as raised:
        await service.update(out.item.id, MemoryItemPatch(title="   "))
    assert raised.value.status_code == 422 and raised.value.code == "memory_content_required"


async def test_create_by_user_is_active_logged_and_idempotent(
    service: MemoryService, db: AsyncSession
) -> None:
    body = MemoryItemCreate(
        kind="decision", title="Cap", text="Viser le back-end.", tags=["carrière"]
    )
    first = await service.create_by_user(body)
    assert first.status == "active" and first.created_by == "user" and first.indexed
    assert first.tags == ["carrière"] and first.reason is None and first.level is None
    again = await service.create_by_user(body)
    writes = await _writes(db)
    assert again.id == first.id and len(writes) == 1
    assert writes[0].author == "user" and writes[0].reason is None


async def test_items_are_isolated_between_users(
    service: MemoryService, db: AsyncSession, runtime: MemoryRuntime
) -> None:
    mine = await service.write(draft(author="writer"))
    other = MemoryService(db, "u2", runtime)
    for call in (
        other.detail(mine.item.id),
        other.update(mine.item.id, MemoryItemPatch(text="Piraté.")),
        other.delete(mine.item.id),
    ):
        with pytest.raises(AppError) as raised:
            await call
        assert raised.value.code == "memory_item_not_found" and raised.value.status_code == 404
    assert (await other.list_items(ALL, limit=50, offset=0)).total == 0
    twin = await other.write(draft(author="writer"))  # même contenu : un autre élément
    assert twin.created and twin.item.id != mine.item.id
    assert await _count(db, MemoryChunk) == 2
    assert (await service.detail(mine.item.id)).text.startswith("L'attention")


async def test_list_items_filters_and_pages(service: MemoryService) -> None:
    await service.write(draft(kind="acquis", author="archivist", title="Python", tags=("python",)))
    await service.write(draft(kind="lecon", author="writer", title="Leçon", tags=("python", "web")))
    await service.create_by_user(MemoryItemCreate(kind="offre", title="Offre", text="Poste."))
    assert (await service.list_items(ALL, limit=50, offset=0)).total == 3
    by_kind = await service.list_items(ItemFilter(kind="acquis"), limit=50, offset=0)
    assert [i.title for i in by_kind.items] == ["Python"]
    assert (await service.list_items(ItemFilter(tag="python"), limit=50, offset=0)).total == 2
    assert (await service.list_items(ItemFilter(author="user"), limit=50, offset=0)).total == 1
    page = await service.list_items(ALL, limit=1, offset=1)
    assert page.total == 3 and len(page.items) == 1
    future = ItemFilter(since=datetime(2100, 1, 1, tzinfo=UTC))
    assert (await service.list_items(future, limit=50, offset=0)).total == 0


async def test_detail_has_chunks_journal_and_neighbors(service: MemoryService) -> None:
    a = await service.write(
        draft(author="writer", title="Attention", text="attention mots phrase modèle")
    )
    b = await service.write(
        draft(author="writer", title="Voisin", text="attention mots phrase modèle langage")
    )
    await service.write(draft(author="writer", title="Loin", text="cuisine tomate basilic four"))
    detail = await service.detail(a.item.id)
    assert [c.ordinal for c in detail.chunks] == [0] and detail.chunks[0].token_count == 4
    assert [(w.action, w.author, w.item_title) for w in detail.writes] == [
        ("create", "writer", "Attention")
    ]
    assert detail.neighbors[0].item_id == b.item.id and detail.neighbors[0].title == "Voisin"
    assert a.item.id not in {n.item_id for n in detail.neighbors}
    assert 0 < detail.neighbors[0].score <= 1
    assert detail.reason == "Leçon publiée." and detail.evidence == []


async def test_neighbors_skip_vectors_without_item(
    service: MemoryService, db: AsyncSession
) -> None:
    a = await service.write(draft(author="writer", title="A", text="attention mots"))
    b = await service.write(draft(author="writer", title="B", text="attention mots phrase"))
    await db.delete(b.item)  # élément supprimé en base, vecteur resté dans l'index
    await db.flush()
    assert (await service.detail(a.item.id)).neighbors == []
