"""API des documents (`/documents`) : import, doublons, réimport, erreurs, isolation."""

import logging
import re
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.core.providers import MemoryProviders
from app.features.memory.repository import DocumentRepository
from app.providers.web.base import UrlForbidden, WebDocument
from scripts.sample_pdf import make_pdf
from tests.features.memory.doc_support import PHRASE
from tests.sessions_support import act_as
from tests.support.memory import FakeWebReader

API = "/api/v1/documents"
SEARCH = "/api/v1/memory/search"
Factory = async_sessionmaker[AsyncSession]


async def _upload(client: httpx.AsyncClient, name: str, data: bytes, mime: str = "") -> Any:
    return await client.post(API, files={"file": (name, data, mime or "application/octet-stream")})


async def _settle(app: FastAPI) -> None:
    await app.state.memory.jobs.join()


async def test_upload_pdf_then_search_finds_it(app: FastAPI, client: httpx.AsyncClient) -> None:
    r = await _upload(client, "cours.pdf", make_pdf([PHRASE]), "application/pdf")
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["duplicate"] is False and body["document"]["status"] == "queued"
    assert body["document"]["name"] == "cours.pdf" and body["document"]["source_kind"] == "pdf"
    await _settle(app)
    doc = (await client.get(API)).json()[0]
    assert doc["status"] == "indexed" and doc["error"] is None
    hits = (await client.post(SEARCH, json={"query": "attention multi-têtes"})).json()["hits"]
    assert hits[0]["item_id"] == doc["item_id"] and hits[0]["kind"] == "document"


async def test_same_file_twice_returns_existing_document(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    first = (await _upload(client, "a.txt", PHRASE.encode())).json()["document"]
    await _settle(app)
    again = await _upload(client, "autre-nom.txt", PHRASE.encode())
    assert again.status_code == 200 and again.json()["duplicate"] is True
    assert again.json()["document"]["id"] == first["id"]
    assert again.json()["document"]["status"] == "indexed"
    assert len((await client.get(API)).json()) == 1


async def test_same_link_twice_is_one_document(app: FastAPI, client: httpx.AsyncClient) -> None:
    first = await client.post(API, data={"url": "https://Example.org/page#haut"})
    second = await client.post(API, data={"url": "HTTPS://EXAMPLE.ORG/page"})
    assert (first.status_code, second.status_code) == (202, 200)
    assert first.json()["document"]["id"] == second.json()["document"]["id"]
    assert first.json()["document"]["url"] == "https://example.org/page"
    assert first.json()["document"]["name"] == "example.org"


async def test_reupload_after_error_requeues(app: FastAPI, client: httpx.AsyncClient) -> None:
    first = (await _upload(client, "court.txt", b"trop court")).json()["document"]
    await _settle(app)
    failed = (await client.get(API)).json()[0]
    assert failed["status"] == "error" and failed["error"]["code"] == "no_text"
    again = await _upload(client, "court.txt", b"trop court")
    assert again.status_code == 202 and again.json()["duplicate"] is False
    doc = again.json()["document"]
    assert doc["id"] == first["id"] and doc["status"] == "queued" and doc["error"] is None
    await _settle(app)
    assert len((await client.get(API)).json()) == 1


async def test_paste_is_stored_as_a_text_file(
    app: FastAPI, client: httpx.AsyncClient, db_session_factory: Factory
) -> None:
    r = await client.post(API, data={"text": PHRASE, "title": "  Mes notes  "})
    assert r.status_code == 202
    doc = r.json()["document"]
    assert doc["source_kind"] == "paste" and doc["name"] == "Mes notes"
    await _settle(app)
    async with db_session_factory() as db:
        row = await DocumentRepository(db, app.state.local_user_id).get(doc["id"])
    assert row is not None and row.storage_key is not None and row.storage_key.endswith(".txt")
    assert (await client.get(API)).json()[0]["status"] == "indexed"


async def test_youtube_link_is_classified(app: FastAPI, client: httpx.AsyncClient) -> None:
    r = await client.post(API, data={"url": "https://youtu.be/dQw4w9WgXcQ"})
    doc = r.json()["document"]
    assert doc["source_kind"] == "youtube" and doc["name"] == "Vidéo YouTube dQw4w9WgXcQ"


async def test_unsupported_type_is_415(client: httpx.AsyncClient, tmp_path: Path) -> None:
    r = await _upload(client, "cv-confidentiel.pdf", b"PK\x03\x04" + b"0" * 64)
    assert r.status_code == 415
    assert r.json()["error"]["code"] == "unsupported_file_type"
    assert "confidentiel" not in r.text
    assert not list((tmp_path / "storage").rglob("*.*"))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"files": {"file": ("a.txt", b"bonjour")}, "data": {"url": "https://example.org/"}},
        {"data": {"url": "https://example.org/", "text": "bonjour"}},
        {"data": {"text": "   "}},
        {"data": {}},
    ],
)
async def test_exactly_one_source_required(client: httpx.AsyncClient, kwargs: Any) -> None:
    r = await client.post(API, **kwargs)
    assert r.status_code == 422
    assert r.json()["error"] == {
        "code": "invalid_document_source",
        "message": "Fournis un fichier, un lien ou un texte (un seul).",
        "details": None,
    }


async def test_validation_error_never_echoes_the_input(client: httpx.AsyncClient) -> None:
    long_url = "https://example.org/" + "secret" * 400
    r = await client.post(API, data={"url": long_url})
    assert r.status_code == 422 and "secret" not in r.text
    bad = await client.post(API, data={"url": "ftp://secret.example/x"})
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "invalid_url"
    assert "secret" not in bad.text


async def test_url_errors_become_document_error_status(
    app: FastAPI, client: httpx.AsyncClient, memory_providers: MemoryProviders
) -> None:
    web = memory_providers.web
    assert isinstance(web, FakeWebReader)
    web.pages["http://10.0.0.1/admin"] = UrlForbidden()
    web.pages["https://example.org/a"] = WebDocument(
        "https://example.org/a", "Article", PHRASE, None, None, None, None
    )
    bad = await client.post(API, data={"url": "http://10.0.0.1/admin"})
    assert bad.status_code == 202
    await client.post(API, data={"url": "https://example.org/a"})
    await _settle(app)
    docs = {d["id"]: d for d in (await client.get(API)).json()}
    failed = docs[bad.json()["document"]["id"]]
    assert failed["status"] == "error" and failed["error"]["code"] == "url_forbidden"
    assert [d["status"] for d in docs.values()].count("indexed") == 1


async def test_filename_never_used_as_path(
    app: FastAPI,
    client: httpx.AsyncClient,
    settings: Settings,
    db_session_factory: Factory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO):
        r = await _upload(client, "../../evil.pdf", make_pdf([PHRASE]))
        await _settle(app)
    doc = r.json()["document"]
    assert doc["name"] == "evil.pdf"
    user = app.state.local_user_id
    async with db_session_factory() as db:
        row = await DocumentRepository(db, user).get(doc["id"])
    assert row is not None and row.storage_key is not None
    assert re.fullmatch(rf"{user}/documents/[0-9a-f-]{{36}}\.pdf", row.storage_key)
    stored = [p for p in settings.data_dir.rglob("*") if p.is_file() and p.suffix == ".pdf"]
    assert stored == [settings.storage_dir / row.storage_key]
    assert "evil" not in caplog.text


async def test_documents_isolated_between_users(app: FastAPI, client: httpx.AsyncClient) -> None:
    await _upload(client, "a.txt", PHRASE.encode())
    await _settle(app)
    mine = (await client.get(API)).json()[0]
    assert mine["item_id"] is not None
    act_as(app, "autre")
    assert (await client.get(API)).json() == []
    theirs = await _upload(client, "a.txt", PHRASE.encode())  # même fichier, autre utilisateur
    assert theirs.status_code == 202 and theirs.json()["document"]["id"] != mine["id"]
    removed = await client.delete(f"/api/v1/memory/items/{mine['item_id']}")
    assert removed.status_code == 404
    await _settle(app)
    assert [d["id"] for d in (await client.get(API)).json()] == [theirs.json()["document"]["id"]]
