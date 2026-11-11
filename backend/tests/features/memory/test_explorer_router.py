"""Explorateur (4.6, 14.2) : carte PCA, statistiques, export JSON ; isolation entre utilisateurs."""

import re
from dataclasses import replace
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.config import Settings
from app.features.memory.service import explorer
from app.features.memory.service.items import MemoryService
from tests.features.memory.helpers import draft, with_vector_store_down
from tests.sessions_support import act_as

ITEMS = "/api/v1/memory/items"
MAP = "/api/v1/memory/map"
STATS = "/api/v1/memory/stats"
EXPORT = "/api/v1/memory/export"
KINDS = {"document", "acquis", "lecon", "source", "offre", "decision"}


async def _create(client: httpx.AsyncClient, kind: str, title: str, text: str) -> str:
    r = await client.post(ITEMS, json={"kind": kind, "title": title, "text": text})
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


async def _agent_decision(app: FastAPI) -> None:
    """Décision proposée par l'Archiviste : en attente de confirmation, jamais indexée."""
    async with app.state.session_factory() as db:
        service = MemoryService(db, app.state.local_user_id, app.state.memory)
        out = await service.write(
            draft(kind="decision", title="Cap", text="Viser Lyon.", author="archivist")
        )
        assert out.item.status == "pending"
        await db.commit()


async def _three_items(client: httpx.AsyncClient) -> list[str]:
    return [
        await _create(client, "acquis", "Python", "Je sais écrire des scripts Python."),
        await _create(client, "offre", "Offre", "Poste de développeur à Lyon."),
        await _create(client, "decision", "Choix", "Apprendre le Rust cette année."),
    ]


async def test_map_returns_one_point_per_active_item(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    ids = await _three_items(client)
    await _agent_decision(app)
    r = await client.get(MAP)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["method"] == "pca" and body["truncated"] is False
    points = {p["item_id"]: p for p in body["points"]}
    assert set(points) == set(ids)
    assert [points[i]["kind"] for i in ids] == ["acquis", "offre", "decision"]
    assert points[ids[0]]["title"] == "Python"
    for p in points.values():
        assert -1.0 <= p["x"] <= 1.0 and -1.0 <= p["y"] <= 1.0


async def test_map_truncates_over_limit(
    monkeypatch: pytest.MonkeyPatch, client: httpx.AsyncClient
) -> None:
    ids = await _three_items(client)
    monkeypatch.setattr(explorer, "MAP_MAX_ITEMS", 2)
    body = (await client.get(MAP)).json()
    assert body["truncated"] is True
    assert {p["item_id"] for p in body["points"]} == set(ids[1:])  # les deux plus récents


async def test_map_when_vector_store_down_is_readable(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    await _three_items(client)
    runtime = app.state.memory
    app.state.memory = replace(runtime, providers=with_vector_store_down(runtime.providers))
    r = await client.get(MAP)
    assert r.status_code == 503 and r.json()["error"]["code"] == "memory_unavailable"


async def test_stats_counts_and_vectorize_share(
    app: FastAPI, client: httpx.AsyncClient, settings: Settings
) -> None:
    await _three_items(client)
    await _agent_decision(app)
    r = await client.get(STATS)
    assert r.status_code == 200, r.text
    s = r.json()
    assert set(s["by_kind"]) == KINDS
    assert s["by_kind"]["acquis"] == 1 and s["by_kind"]["lecon"] == 0
    assert s["total_items"] == 3 and s["total_chunks"] == 3 and s["unindexed_items"] == 0
    assert s["dimension"] == 1024 and s["vectorize_limit"] == 5_000_000
    assert s["vectorize_share"] == pytest.approx(s["total_chunks"] * 1024 / 5_000_000)
    assert s["pending_decisions"] == 1 and s["last_write"]["author"] == "archivist"
    assert s["dashboard_url"] == settings.qdrant_dashboard_url
    assert s["reindex"] == {"status": "idle", "done": 0, "total": 0, "error": None}


async def test_export_contains_items_documents_writes_without_vectors(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    ids = await _three_items(client)
    await _agent_decision(app)
    pasted = await client.post("/api/v1/documents/text", json={"text": "Notes " * 20})
    assert pasted.status_code == 202, pasted.text
    await app.state.memory.jobs.join()
    r = await client.get(EXPORT)
    assert r.status_code == 200, r.text
    assert re.fullmatch(
        r'attachment; filename="tremplin-memoire-\d{4}-\d{2}-\d{2}\.json"',
        r.headers["content-disposition"],
    )
    body: dict[str, Any] = r.json()
    assert set(body) == {"version", "exported_at", "items", "documents", "writes"}
    assert "vector" not in r.text and body["version"] == 1
    exported = {i["id"]: i for i in body["items"]}
    assert set(ids) <= set(exported) and len(exported) == 5  # 3 + décision en attente + document
    assert {i["status"] for i in exported.values()} == {"active", "pending"}
    assert [d["status"] for d in body["documents"]] == ["indexed"]
    assert len(body["writes"]) == 5 and {w["action"] for w in body["writes"]} == {"create"}


async def test_explorer_routes_are_isolated_between_users(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    await _three_items(client)
    await _agent_decision(app)
    act_as(app, "autre")
    assert (await client.get(MAP)).json() == {"points": [], "method": "pca", "truncated": False}
    s = (await client.get(STATS)).json()
    assert s["total_items"] == 0 and s["total_chunks"] == 0 and s["pending_decisions"] == 0
    assert s["last_write"] is None and set(s["by_kind"].values()) == {0}
    body = (await client.get(EXPORT)).json()
    assert (body["items"], body["documents"], body["writes"]) == ([], [], [])
    assert (await client.post("/api/v1/memory/reindex")).status_code == 202
    await app.state.memory.jobs.join()
    app.dependency_overrides.clear()
    assert len((await client.get(MAP)).json()["points"]) == 3  # vecteurs du premier intacts
    assert (await client.get(STATS)).json()["reindex"]["status"] == "idle"
