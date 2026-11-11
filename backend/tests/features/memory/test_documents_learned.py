"""« Déjà appris » (`POST /documents/{id}/learned`) : session de l'Archiviste, drapeau, refus, et
l'auteur et la raison d'une écriture d'agent visibles dans l'explorateur (critère de fin 2.9)."""

import json
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from scripts.sample_pdf import make_pdf
from tests.features.memory.doc_support import PHRASE
from tests.sessions_support import act_as, use_test_runtime, wait_status

DOCUMENTS = "/api/v1/documents"
MEMORY = "/api/v1/memory/items"
CONCEPTS = json.dumps(
    {
        "concepts": [
            {"title": "Attention multi-têtes", "summary": "Relie les mots.", "tags": ["nlp"]},
            {"title": "Transformeur", "summary": "Une architecture.", "tags": []},
        ]
    }
)


@pytest.fixture
def archivist_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """Faux LLM scripté pour le moteur du lifespan, branché avant le démarrage de l'app."""
    use_test_runtime(monkeypatch, [CONCEPTS] * 3)


async def _indexed(
    app: FastAPI, client: httpx.AsyncClient, name: str = "cours.pdf"
) -> dict[str, Any]:
    files = {"file": (name, make_pdf([PHRASE]), "application/pdf")}
    assert (await client.post(DOCUMENTS, files=files)).status_code == 202
    await app.state.memory.jobs.join()
    doc: dict[str, Any] = (await client.get(DOCUMENTS)).json()[0]
    assert doc["status"] == "indexed" and doc["learned"] is False
    return doc


async def test_mark_learned_starts_session_and_sets_flag(
    archivist_llm: None, app: FastAPI, client: httpx.AsyncClient
) -> None:
    doc = await _indexed(app, client)
    r = await client.post(f"{DOCUMENTS}/{doc['id']}/learned")
    assert r.status_code == 202 and list(r.json()) == ["session_id"]
    sid = r.json()["session_id"]
    view = await wait_status(client, sid, "completed")
    assert view["graph"] == "learned_document"
    assert (await client.get(DOCUMENTS)).json()[0]["learned"] is True
    sessions = (await client.get("/api/v1/sessions", params={"graph": "learned_document"})).json()
    assert [s["id"] for s in sessions] == [sid]


async def test_mark_learned_requires_indexed_document(
    archivist_llm: None, app: FastAPI, client: httpx.AsyncClient
) -> None:
    created = await client.post(f"{DOCUMENTS}/text", json={"text": "trop court", "title": "T"})
    doc_id = created.json()["document"]["id"]
    await app.state.memory.jobs.join()
    assert (await client.get(DOCUMENTS)).json()[0]["status"] == "error"
    r = await client.post(f"{DOCUMENTS}/{doc_id}/learned")
    assert r.status_code == 409 and r.json()["error"]["code"] == "document_not_ready"
    assert (await client.get(DOCUMENTS)).json()[0]["learned"] is False
    assert (await client.get("/api/v1/sessions")).json() == []


async def test_mark_learned_unknown_or_foreign_document_is_404(
    archivist_llm: None, app: FastAPI, client: httpx.AsyncClient
) -> None:
    doc = await _indexed(app, client)
    missing = await client.post(f"{DOCUMENTS}/inconnu/learned")
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "document_not_found"
    act_as(app, "autre")
    foreign = await client.post(f"{DOCUMENTS}/{doc['id']}/learned")
    assert foreign.status_code == 404 and foreign.json()["error"]["code"] == "document_not_found"
    assert (await client.get("/api/v1/sessions")).json() == []


async def test_agent_write_shows_author_and_reason(
    archivist_llm: None, app: FastAPI, client: httpx.AsyncClient
) -> None:
    doc = await _indexed(app, client, "Cours NLP.pdf")
    sid = (await client.post(f"{DOCUMENTS}/{doc['id']}/learned")).json()["session_id"]
    await wait_status(client, sid, "completed")
    listed = (await client.get(MEMORY, params={"author": "archivist"})).json()
    assert listed["total"] == 2
    item = listed["items"][0]
    assert item["kind"] == "acquis" and item["level"] == "declare" and item["indexed"] is True
    detail = (await client.get(f"{MEMORY}/{item['id']}")).json()
    assert detail["writes"][0]["author"] == "archivist"
    assert "déjà appris" in detail["writes"][0]["reason"]
    assert detail["writes"][0]["session_id"] == sid
    assert detail["source_id"] == doc["id"] and detail["evidence"] == [doc["id"]]
    found = (await client.post("/api/v1/memory/search", json={"query": "Transformeur"})).json()
    assert any(hit["title"] == "Transformeur" for hit in found["hits"])
    again = (await client.post(f"{DOCUMENTS}/{doc['id']}/learned")).json()["session_id"]
    await wait_status(client, again, "completed")  # double clic : rien de plus en mémoire
    assert (await client.get(MEMORY, params={"author": "archivist"})).json()["total"] == 2
