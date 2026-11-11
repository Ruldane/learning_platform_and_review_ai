"""API des documents : limite de 20 Mo, suppression d'un document, services en panne."""

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI

from app.config import Settings
from app.core.providers import MemoryProviders
from app.features.memory.service.sources.base import Extracted, ExtractionTools, SourceInput
from app.features.memory.service.sources.registry import INGESTION_SOURCES
from app.main import create_app
from tests.features.memory.doc_support import PHRASE
from tests.features.memory.helpers import with_embeddings_down

API = "/api/v1/documents"
MAX = 20 * 1024 * 1024
TOO_LARGE = "Fichier trop volumineux : 20 Mo au maximum."


def _stored(tmp_path: Path) -> list[Path]:
    return [p for p in (tmp_path / "storage").rglob("*") if p.is_file()]


async def test_upload_over_20_mb_is_413(client: httpx.AsyncClient, tmp_path: Path) -> None:
    """Sous la limite du corps (20 Mo + 1 Mio d'enveloppe) : c'est la lecture du fichier qui
    refuse. Rien n'est enregistré."""
    data = b"%PDF-" + b"0" * (20 * 1024 * 1024)
    r = await client.post(API, files={"file": ("gros.pdf", data, "application/pdf")})
    assert r.status_code == 413 and r.json()["error"]["message"] == TOO_LARGE
    assert r.json()["error"]["code"] == "file_too_large"
    assert _stored(tmp_path) == []


async def test_body_far_over_the_limit_is_413(client: httpx.AsyncClient) -> None:
    """Au-delà de 21 Mio, le middleware refuse avant toute analyse du multipart."""
    data = b"%PDF-" + b"0" * (MAX + 2 * 1024 * 1024)
    r = await client.post(API, files={"file": ("gros.pdf", data, "application/pdf")})
    assert r.status_code == 413 and r.json()["error"]["message"] == TOO_LARGE


class _Quick:
    kind = "text"

    async def extract(self, source: SourceInput, tools: ExtractionTools) -> Extracted:
        return Extracted(title="gros", text=PHRASE)


async def test_upload_of_exactly_20_mb_is_accepted(
    app: FastAPI, client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(INGESTION_SOURCES, "text", _Quick())
    r = await client.post(API, files={"file": ("gros.txt", b"a" * MAX, "text/plain")})
    assert r.status_code == 202, r.text[:200]
    assert r.json()["document"]["size_bytes"] == MAX
    await app.state.memory.jobs.join()


async def test_delete_document_item_removes_document_and_file(
    app: FastAPI, client: httpx.AsyncClient, tmp_path: Path
) -> None:
    await client.post(API, files={"file": ("a.txt", PHRASE.encode(), "text/plain")})
    await app.state.memory.jobs.join()
    doc = (await client.get(API)).json()[0]
    assert doc["status"] == "indexed" and len(_stored(tmp_path)) == 1
    r = await client.delete(f"/api/v1/memory/items/{doc['item_id']}")
    assert r.status_code == 204
    assert (await client.get(API)).json() == []
    assert _stored(tmp_path) == []
    again = await client.post(API, files={"file": ("a.txt", PHRASE.encode(), "text/plain")})
    assert again.status_code == 202  # réimportable après suppression


@pytest.fixture
async def client_embeddings_down(
    settings: Settings, db_engine: object, memory_providers: MemoryProviders
) -> AsyncIterator[tuple[FastAPI, httpx.AsyncClient]]:
    down = create_app(settings, memory_providers=with_embeddings_down(memory_providers))
    async with LifespanManager(down):
        transport = httpx.ASGITransport(app=down, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield down, c


async def test_embeddings_down_marks_error_never_500(
    client_embeddings_down: tuple[FastAPI, httpx.AsyncClient],
) -> None:
    app, client = client_embeddings_down
    r = await client.post(API, files={"file": ("a.txt", PHRASE.encode(), "text/plain")})
    assert r.status_code == 202
    await app.state.memory.jobs.join()
    listing = await client.get(API)
    assert listing.status_code == 200
    doc = listing.json()[0]
    assert doc["status"] == "error" and doc["item_id"] is not None
    assert doc["error"]["code"] == "embeddings_unavailable"
    assert doc["error"]["message"].startswith("Le service d'embeddings (Ollama) est indisponible")


async def test_concurrent_identical_uploads_make_one_document(
    app: FastAPI, client: httpx.AsyncClient, tmp_path: Path
) -> None:
    """Course sur `source_hash` : l'unicité tranche, la perdante rend le gagnant (200) et
    supprime le fichier qu'elle avait enregistré."""
    files = {"file": ("a.txt", PHRASE.encode(), "text/plain")}
    first, second = await asyncio.gather(
        client.post(API, files=files), client.post(API, files=files)
    )
    assert sorted((first.status_code, second.status_code)) == [200, 202]
    assert first.json()["document"]["id"] == second.json()["document"]["id"]
    await app.state.memory.jobs.join()
    assert len((await client.get(API)).json()) == 1
    assert len(_stored(tmp_path)) == 1


async def test_streamed_multipart_over_the_limit_is_413(
    client: httpx.AsyncClient, tmp_path: Path
) -> None:
    """Corps en flux sans `Content-Length` : le middleware compte les octets pendant l'analyse du
    multipart par FastAPI et remplace sa réponse par la 413."""
    head = (
        b'--xyz\r\nContent-Disposition: form-data; name="file"; filename="a.pdf"\r\n'
        b"Content-Type: application/pdf\r\n\r\n%PDF-"
    )

    async def body() -> AsyncIterator[bytes]:
        yield head
        for _ in range(22):
            yield b"0" * (1024 * 1024)
        yield b"\r\n--xyz--\r\n"

    headers = {"content-type": "multipart/form-data; boundary=xyz"}
    r = await client.post(API, content=body(), headers=headers)
    assert r.status_code == 413 and r.json()["error"]["message"] == TOO_LARGE
    assert _stored(tmp_path) == []
