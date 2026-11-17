"""Les journaux de l'export : identifiants, nombres et durée ; jamais un nom de fichier, un
contenu ni une adresse e-mail."""

import logging
import re

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.accounts import User
from app.db.models.learning import Goal
from app.providers.storage.base import FileStorage
from tests.support.account import API, export_archive, seed_user

SECRET = "contenu-ultra-secret"
LOGGER = "app.features.account.service.export"


async def test_export_never_logged(
    caplog: pytest.LogCaptureFixture,
    client: httpx.AsyncClient,
    app: FastAPI,
    db_session: AsyncSession,
) -> None:
    me: str = app.state.local_user_id
    storage: FileStorage = app.state.memory_providers.storage
    user = await db_session.get(User, me)
    assert user is not None
    user.email, user.name = "camille.exemple@example.org", "Camille Exemple"
    db_session.add(Goal(user_id=me, text=SECRET))
    await seed_user(db_session, me, "tag-secret", app.state.cipher.encrypt("sk-cle-secrete-123"))
    key = await storage.save(me, "documents", SECRET.encode(), ".txt")
    caplog.set_level(logging.DEBUG)

    response = await client.get(API)
    assert response.status_code == 200
    archive = await export_archive(client)
    assert archive.read(f"files/{key}") == SECRET.encode()

    logged = "\n".join(
        f"{record.name} {record.getMessage()} {record.exc_text or ''}" for record in caplog.records
    )
    filename = response.headers["content-disposition"].split('"')[1]
    for secret in (
        SECRET,
        "tag-secret",
        "sk-cle-secrete-123",
        "camille.exemple@example.org",
        "Camille",
        filename,
        "tremplin-export",
        ".zip",
        key.rsplit("/", 1)[1],  # le nom du fichier déposé
        "encrypted_key",
    ):
        assert secret not in logged, secret


async def test_export_logs_ids_counts_and_duration(
    caplog: pytest.LogCaptureFixture,
    client: httpx.AsyncClient,
    app: FastAPI,
    db_session: AsyncSession,
) -> None:
    me: str = app.state.local_user_id
    storage: FileStorage = app.state.memory_providers.storage
    await seed_user(db_session, me, "moi", "jeton")
    await storage.save(me, "documents", b"a", ".pdf")
    await storage.save(me, "documents", b"b", ".pdf")
    caplog.set_level(logging.INFO, logger="app")
    await export_archive(client)
    [record] = [r for r in caplog.records if r.name == LOGGER]
    message = record.getMessage()
    assert f"user={me}" in message and "files=2" in message
    assert re.search(r"tables=\d+", message) and re.search(r"rows=\d+", message)
    assert re.search(r"duration_ms=\d+", message)
