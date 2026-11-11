"""Fusion d'éléments (4.6, D67) : texte, étiquettes, preuves et niveau réunis, autres supprimés
et journalisés, cible journalisée `merge` et réindexée."""

from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.memory import MemoryItem
from app.features.memory.repository import ChunkRepository, MemoryItemRepository, WriteRepository
from app.features.memory.schemas import SearchRequest
from app.features.memory.service.items import MemoryService
from app.features.memory.service.merge import merge
from app.features.memory.service.runtime import MemoryRuntime
from app.features.memory.service.search import search
from tests.features.memory.helpers import draft
from tests.sessions_support import act_as

API = "/api/v1/memory/items"


async def _write(service: MemoryService, **fields: Any) -> MemoryItem:
    values: dict[str, Any] = {"author": "user", "reason": None, **fields}
    return (await service.write(draft(**values))).item


async def _vectors(runtime: MemoryRuntime, item_id: str) -> int:
    records = await runtime.providers.index.vectors("u1", limit=10_000)
    return sum(1 for r in records if r.payload.item_id == item_id)


async def test_merge_combines_text_tags_and_deletes_others(
    service: MemoryService, db: AsyncSession, runtime: MemoryRuntime
) -> None:
    # Acquis : reconnus à leur titre, deux acquis peuvent porter le même texte.
    acquis = {"kind": "acquis", "level": "declare"}
    target = await _write(
        service, title="Cible", text="A", tags=("nlp",), evidence=("e1",), **acquis
    )
    other = await _write(
        service, title="Autre", text="B", tags=("nlp", "python"), evidence=("e2", "e1"), **acquis
    )
    # Même texte que la cible, à la casse près : pas recopié.
    twin = await _write(service, title="Jumeau", text="a", **acquis)

    out = await merge(service, target.id, [other.id, twin.id])
    await db.commit()

    assert out.text == "A\n\nB" and out.tags == ["nlp", "python"]
    assert out.evidence == ["e1", "e2"] and out.indexed is True
    target_writes = await WriteRepository(db, "u1").for_item(target.id)
    assert [(w.action, w.reason) for w in target_writes][0] == ("merge", "Fusion de 2 élément(s).")
    for gone in (other, twin):
        assert await MemoryItemRepository(db, "u1").get(gone.id) is None
        assert await ChunkRepository(db, "u1").for_item(gone.id) == []
        assert await _vectors(runtime, gone.id) == 0
        log = await WriteRepository(db, "u1").for_item(gone.id)
        assert [(w.action, w.reason) for w in log][0] == ("delete", "Fusionné dans « Cible ».")
    assert await _vectors(runtime, target.id) == 1
    found = await search(db, "u1", runtime, SearchRequest(query="B"))
    assert [h.item_id for h in found.hits] == [target.id]


async def test_merge_requires_same_kind(service: MemoryService) -> None:
    target = await _write(service, kind="lecon", title="Leçon")
    other = await _write(service, kind="offre", title="Offre", text="Poste à Lyon.")
    with pytest.raises(AppError) as err:
        await merge(service, target.id, [other.id])
    assert (err.value.code, err.value.status_code) == ("merge_kind_mismatch", 422)
    assert err.value.message == "On ne fusionne que des éléments du même type."


async def test_merge_rejects_documents(service: MemoryService) -> None:
    target = await _write(service, kind="document", title="Doc 1", text="Premier document.")
    other = await _write(service, kind="document", title="Doc 2", text="Second document.")
    with pytest.raises(AppError) as err:
        await merge(service, target.id, [other.id])
    assert (err.value.code, err.value.status_code) == ("merge_document_forbidden", 409)
    assert err.value.message == "Un document ne se fusionne pas : supprime le doublon."


async def test_merge_acquis_keeps_highest_level(service: MemoryService) -> None:
    target = await _write(service, kind="acquis", title="Python", text="Scripts.", level="declare")
    other = await _write(service, kind="acquis", title="Python 2", text="API.", level="en_cours")
    out = await merge(service, target.id, [other.id])
    assert out.level == "en_cours" and out.kind == "acquis"


async def test_merge_refuses_pending_and_self(service: MemoryService) -> None:
    target = await _write(service, kind="decision", title="Cap", text="Viser Paris.")
    pending = await _write(
        service, kind="decision", title="Cap 2", text="Viser Lyon.", author="coach", reason="r"
    )
    assert pending.status == "pending"
    with pytest.raises(AppError) as err:
        await merge(service, target.id, [pending.id])
    assert (err.value.code, err.value.status_code) == ("merge_pending_forbidden", 409)
    with pytest.raises(AppError) as err:
        await merge(service, target.id, [target.id])
    assert (err.value.code, err.value.status_code) == ("merge_nothing", 422)


async def test_merge_route_and_isolation(app: FastAPI, client: httpx.AsyncClient) -> None:
    async def create(title: str, text: str) -> str:
        body = {"kind": "offre", "title": title, "text": text}
        r = await client.post(API, json=body)
        assert r.status_code == 201, r.text
        return str(r.json()["id"])

    target, other = await create("Offre", "Poste A."), await create("Offre 2", "Poste B.")
    act_as(app, "autre")
    stranger = await create("Offre", "Poste A.")
    r = await client.post(f"{API}/{stranger}/merge", json={"other_ids": [other]})
    assert r.status_code == 404 and r.json()["error"]["code"] == "memory_item_not_found"
    r = await client.post(f"{API}/{target}/merge", json={"other_ids": [stranger]})
    assert r.status_code == 404
    app.dependency_overrides.clear()

    secret = "secret-" + "x" * 41
    for bad in ([], secret, [other] * 21):
        r = await client.post(f"{API}/{target}/merge", json={"other_ids": bad})
        assert r.status_code == 422 and secret not in r.text and other not in r.text
    r = await client.post(f"{API}/{target}/merge", json={"other_ids": [other]})
    assert r.status_code == 200, r.text
    assert r.json()["text"] == "Poste A.\n\nPoste B." and r.json()["id"] == target
    assert (await client.get(f"{API}/{other}")).status_code == 404
    act_as(app, "autre")
    assert (await client.get(f"{API}/{stranger}")).status_code == 200  # intact chez l'autre


async def test_merge_into_existing_content_is_refused_and_rolled_back(
    client: httpx.AsyncClient,
) -> None:
    ids = []
    merged = "Poste A.\n\nPoste B."
    for title, text in (("A", "Poste A."), ("B", "Poste B."), ("AB", merged)):
        r = await client.post(API, json={"kind": "offre", "title": title, "text": text})
        assert r.status_code == 201, r.text
        ids.append(r.json()["id"])
    r = await client.post(f"{API}/{ids[0]}/merge", json={"other_ids": [ids[1]]})
    assert r.status_code == 409 and r.json()["error"]["code"] == "memory_duplicate"
    for item_id in ids:  # rien supprimé, rien modifié
        assert (await client.get(f"{API}/{item_id}")).status_code == 200
    assert (await client.get(f"{API}/{ids[0]}")).json()["writes"][0]["action"] == "create"
