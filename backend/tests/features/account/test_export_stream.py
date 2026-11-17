"""`GET /account/export` : le nom du fichier, le flux par morceaux, le fichier temporaire, le
verrou par compte et le contrat."""

import asyncio
import os
import tempfile
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.accounts import UserSettingsRow
from app.features.account.service import export as export_module
from app.features.account.service.export import (
    CHUNK_BYTES,
    SPOOL_MAX_BYTES,
    export_filename,
    export_lock,
    stream_export,
)
from app.providers.storage.base import FileStorage
from tests.support.account import API, OTHER, export_archive


@pytest.fixture
def storage(app: FastAPI) -> FileStorage:
    files: FileStorage = app.state.memory_providers.storage
    return files


def test_export_filename_uses_the_local_day() -> None:
    late = datetime(2026, 11, 17, 23, 30, tzinfo=UTC)
    assert export_filename(late, ZoneInfo("UTC")) == "tremplin-export-20261117.zip"
    assert export_filename(late, ZoneInfo("Europe/Paris")) == "tremplin-export-20261118.zip"
    assert export_filename(late, ZoneInfo("America/New_York")) == "tremplin-export-20261117.zip"


async def test_export_filename_follows_the_user_timezone(
    client: httpx.AsyncClient, app: FastAPI, db_session: AsyncSession
) -> None:
    me: str = app.state.local_user_id
    db_session.add(UserSettingsRow(user_id=me, data={"timezone": "Pacific/Kiritimati"}))
    await db_session.commit()
    before = export_filename(datetime.now(UTC), ZoneInfo("Pacific/Kiritimati"))
    response = await client.get(API)
    after = export_filename(datetime.now(UTC), ZoneInfo("Pacific/Kiritimati"))
    disposition = response.headers["content-disposition"]
    assert disposition in (f'attachment; filename="{before}"', f'attachment; filename="{after}"')
    paris = export_filename(datetime.now(UTC), ZoneInfo("Pacific/Pago_Pago"))
    assert paris not in disposition  # 25 heures d'écart : jamais le même jour


async def test_stream_comes_in_chunks_of_64_kib() -> None:
    assert CHUNK_BYTES == 64 * 1024
    data = os.urandom(CHUNK_BYTES * 3 + 123)
    spool = tempfile.SpooledTemporaryFile(max_size=1024)  # noqa: SIM115  (le flux le ferme)
    spool.write(data)
    spool.seek(0)
    chunks = [chunk async for chunk in stream_export(spool)]
    assert [len(c) for c in chunks] == [CHUNK_BYTES] * 3 + [123]
    assert b"".join(chunks) == data and spool.closed


async def test_stream_closes_the_file_when_the_client_leaves() -> None:
    spool = tempfile.SpooledTemporaryFile(max_size=1024)  # noqa: SIM115
    spool.write(os.urandom(CHUNK_BYTES * 2))
    spool.seek(0)
    stream = stream_export(spool)
    await anext(stream)
    await stream.aclose()
    assert spool.closed


def test_the_archive_stays_in_memory_up_to_32_mib() -> None:
    assert SPOOL_MAX_BYTES == 32 * 1024 * 1024


async def test_export_spills_to_disk_over_the_memory_limit(
    client: httpx.AsyncClient,
    app: FastAPI,
    storage: FileStorage,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    me: str = app.state.local_user_id
    payload = os.urandom(5000)
    key = await storage.save(me, "documents", payload, ".pdf")
    rolled: list[bool] = []
    real = tempfile.SpooledTemporaryFile

    def spy(*args: Any, **kwargs: Any) -> Any:
        spool = real(*args, **kwargs)
        assert kwargs["max_size"] == 1024
        rolled.append(True)
        return spool

    monkeypatch.setattr(export_module, "SPOOL_MAX_BYTES", 1024)
    monkeypatch.setattr(export_module.tempfile, "SpooledTemporaryFile", spy)
    archive = await export_archive(client)
    assert rolled == [True] and archive.read(f"files/{key}") == payload


async def test_two_exports_of_one_user_run_one_at_a_time(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    me: str = app.state.local_user_id
    assert (await client.get(API)).status_code == 200  # crée les verrous
    async with export_lock(app.state.account_locks, me):
        waiting = asyncio.create_task(client.get(API))
        await asyncio.sleep(0.2)
        assert not waiting.done()
        assert not export_lock(app.state.account_locks, OTHER).locked()  # autre compte : libre
    response = await asyncio.wait_for(waiting, 5)
    assert response.status_code == 200


async def test_a_failed_build_releases_the_lock(
    client: httpx.AsyncClient, app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.features.account import router as router_module

    async def boom(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("secret-ultra-valeur")

    with monkeypatch.context() as patch:
        patch.setattr(router_module, "build_export", boom)
        failed = await client.get(API)
    assert failed.status_code == 500 and "secret-ultra-valeur" not in failed.text
    assert not export_lock(app.state.account_locks, app.state.local_user_id).locked()
    assert (await client.get(API)).status_code == 200


async def test_export_in_google_mode_without_session_is_401(
    client_google_mode: httpx.AsyncClient,
) -> None:
    response = await client_google_mode.get(API)
    assert response.status_code == 401 and response.json()["error"]["code"] == "auth_required"


def test_export_documents_its_content_disposition_header(app: FastAPI) -> None:
    operation = app.openapi()["paths"]["/api/v1/account/export"]["get"]
    ok = operation["responses"]["200"]
    assert "application/zip" in ok["content"]
    header = ok["headers"]["Content-Disposition"]
    assert header["schema"]["type"] == "string"
    assert "tremplin-export-AAAAMMJJ.zip" in header["description"]
