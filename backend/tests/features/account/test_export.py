"""`GET /account/export` : le contenu de l'archive, l'isolation entre comptes, aucun secret,
la forme du flux et le verrou."""

import re
from collections.abc import AsyncIterator
from datetime import datetime

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import Column, String, Table
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.db.base import Base
from app.providers.storage.base import FileStorage
from tests.support.account import (
    API,
    OTHER,
    Archive,
    as_other,
    export_archive,
    seed_other_user,
    seed_user,
)

KEY_PLAIN = "sk-cle-en-clair-0123456789"


@pytest.fixture
def storage(app: FastAPI) -> FileStorage:
    files: FileStorage = app.state.memory_providers.storage
    return files


async def test_export_zip_has_manifest_tables_and_files(
    client: httpx.AsyncClient,
    app: FastAPI,
    db_session: AsyncSession,
    storage: FileStorage,
) -> None:
    me: str = app.state.local_user_id
    await seed_user(db_session, me, "moi", app.state.cipher.encrypt(KEY_PLAIN))
    pdf = await storage.save(me, "documents", b"%PDF-contenu", ".pdf")
    png = await storage.save(me, "screenshots", b"\x89PNG-contenu", ".png")

    response = await client.get(API)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert re.fullmatch(
        r'attachment; filename="tremplin-export-\d{8}\.zip"',
        response.headers["content-disposition"],
    )
    assert response.headers["content-length"] == str(len(response.content))
    assert response.headers["cache-control"] == "no-store"
    archive = Archive(response.content)
    assert archive.zip.testzip() is None
    prefix, suffix = "tables/", ".json"
    tables = {n[len(prefix) : -len(suffix)] for n in archive.names if n.startswith(prefix)}
    assert {"users", "user_settings", "api_keys", "llm_calls", "goals", "memory_items"} <= tables
    assert "auth_sessions" not in tables
    assert archive.read(f"files/{pdf}") == b"%PDF-contenu"
    assert archive.read(f"files/{png}") == b"\x89PNG-contenu"
    manifest = archive.manifest
    assert manifest["format_version"] == 1 and manifest["user_id"] == me
    assert manifest["files"] == 2
    assert manifest["tables"]["goals"] == 1 and manifest["tables"]["users"] == 1
    assert manifest["tables"] == {name: len(archive.table(name)) for name in manifest["tables"]}
    assert set(manifest["tables"]) == tables
    assert datetime.fromisoformat(manifest["exported_at"]).tzinfo is not None
    [goal] = archive.table("goals")
    assert goal["text"] == "objectif-moi" and goal["framing"] == {"q": ["moi"]}
    assert goal["created_at"].endswith("+00:00") and goal["deadline"] is None


async def test_export_of_an_empty_account_is_a_valid_archive(client: httpx.AsyncClient) -> None:
    archive = await export_archive(client)
    assert archive.manifest["files"] == 0
    assert archive.table("goals") == [] and archive.table("api_keys") == []
    assert not [name for name in archive.names if name.startswith("files/")]


async def test_export_has_only_own_rows(
    client: httpx.AsyncClient,
    app: FastAPI,
    db_session: AsyncSession,
    storage: FileStorage,
) -> None:
    me: str = app.state.local_user_id
    await seed_other_user(db_session)
    await seed_user(db_session, me, "moi", "jeton-moi")
    await seed_user(db_session, OTHER, "autre", "jeton-autre")
    mine = await storage.save(me, "documents", b"fichier-moi", ".txt")
    theirs = await storage.save(OTHER, "documents", b"fichier-autre", ".txt")

    mine_archive = await export_archive(client)
    as_other(app)
    theirs_archive = await export_archive(client)

    for archive, owner, tag, other_tag, own_file, foreign_file in (
        (mine_archive, me, "moi", "autre", mine, theirs),
        (theirs_archive, OTHER, "autre", "moi", theirs, mine),
    ):
        assert archive.manifest["user_id"] == owner
        for name in archive.manifest["tables"]:
            assert {row["user_id"] for row in archive.table(name)} <= {owner}, name
        assert [row["text"] for row in archive.table("goals")] == [f"objectif-{tag}"]
        assert [row["model"] for row in archive.table("llm_calls")] == [f"modele-{tag}"]
        assert [row["title"] for row in archive.table("memory_items")] == [f"titre-{tag}"]
        assert [row["id"] for row in archive.table("users")] == [owner]
        content = archive.text()
        assert f"-{other_tag}" not in content.replace(OTHER, "").replace("moi-", "")
        assert f"fichier-{other_tag}" not in content
        assert archive.read(f"files/{own_file}") == f"fichier-{tag}".encode()
        assert f"files/{foreign_file}" not in archive.names
        assert foreign_file not in content
    assert "dominique.exemple@example.org" in theirs_archive.text()
    assert "dominique.exemple@example.org" not in mine_archive.text()


async def test_export_never_contains_encrypted_key(
    client: httpx.AsyncClient, app: FastAPI, db_session: AsyncSession
) -> None:
    me: str = app.state.local_user_id
    token = app.state.cipher.encrypt(KEY_PLAIN)
    other_token = app.state.cipher.encrypt("sk-autre-cle-9876543210")
    await seed_other_user(db_session)
    await seed_user(db_session, me, "moi", token)
    await seed_user(db_session, OTHER, "autre", other_token)

    response = await client.get(API)
    archive = Archive(response.content)

    [api_key] = archive.table("api_keys")
    assert api_key["provider"] == "glm" and api_key["last4"] == "wxyz"
    assert "encrypted_key" not in api_key
    content = archive.text()
    for secret in (
        "encrypted_key",
        token,
        other_token,
        KEY_PLAIN,
        "sk-autre-cle",
        "hash-session-moi",
        "hash-session-autre",
        "token_hash",
        "auth_sessions",
    ):
        # Dans l'archive ouverte (les entrées sont compressées) et dans ses octets bruts.
        assert secret not in content, secret
        assert secret.encode() not in response.content, secret
    # Le secret de l'application, lui non plus, ne sort jamais.
    secret_file = app.state.settings.data_dir / "secret.key"
    if secret_file.exists():
        assert secret_file.read_bytes().strip().decode() not in content


async def test_export_files_of_other_user_absent(
    client: httpx.AsyncClient, app: FastAPI, storage: FileStorage
) -> None:
    me: str = app.state.local_user_id
    mine = await storage.save(me, "documents", b"a", ".pdf")
    await storage.save(OTHER, "documents", b"b", ".pdf")
    await storage.save(OTHER, "screenshots", b"c", ".png")
    archive = await export_archive(client)
    assert [n for n in archive.names if n.startswith("files/")] == [f"files/{mine}"]
    assert OTHER not in archive.text()


async def test_export_new_table_needs_no_change(
    client: httpx.AsyncClient, app: FastAPI, db_engine: AsyncEngine, extra_table: Table
) -> None:
    me: str = app.state.local_user_id
    async with db_engine.begin() as conn:
        await conn.execute(extra_table.insert().values(id="1", user_id=me, label="demain"))
        await conn.execute(extra_table.insert().values(id="2", user_id=OTHER, label="autrui"))
    archive = await export_archive(client)
    assert archive.table("future_things") == [{"id": "1", "user_id": me, "label": "demain"}]
    assert archive.manifest["tables"]["future_things"] == 1
    assert "autrui" not in archive.text()


@pytest.fixture
async def unscoped_table(db_engine: AsyncEngine) -> AsyncIterator[Table]:
    table = Table("unscoped_things", Base.metadata, Column("id", String(36), primary_key=True))
    async with db_engine.begin() as conn:
        await conn.run_sync(table.create)
    yield table
    async with db_engine.begin() as conn:
        await conn.run_sync(table.drop)
    Base.metadata.remove(table)


async def test_export_ignores_tables_without_user_id(
    client: httpx.AsyncClient, unscoped_table: Table
) -> None:
    archive = await export_archive(client)
    assert "tables/unscoped_things.json" not in archive.names
    assert "unscoped_things" not in archive.manifest["tables"]


class GhostStorage:
    """Un stockage qui liste une clé de plus que ce qu'il a : fichier effacé entre-temps."""

    def __init__(self, inner: FileStorage, ghost: str) -> None:
        self.inner, self.ghost = inner, ghost

    async def save(self, user_id: str, category: str, data: bytes, suffix: str) -> str:
        return await self.inner.save(user_id, category, data, suffix)

    async def read(self, user_id: str, key: str) -> bytes:
        return await self.inner.read(user_id, key)

    async def delete(self, user_id: str, key: str) -> None:
        await self.inner.delete(user_id, key)

    async def list_user(self, user_id: str) -> list[str]:
        return [*await self.inner.list_user(user_id), self.ghost]


async def test_export_skips_a_file_deleted_in_the_meantime(
    client: httpx.AsyncClient, app: FastAPI, storage: FileStorage
) -> None:
    me: str = app.state.local_user_id
    real = await storage.save(me, "documents", b"reste", ".txt")
    ghost = f"{me}/documents/0b8a7c1e-4c4e-4a4f-9a7e-2f0d7e0c1a2b.txt"
    providers = app.state.memory_providers
    app.state.memory_providers = type(providers)(
        **{**vars(providers), "storage": GhostStorage(storage, ghost)}
    )
    archive = await export_archive(client)
    assert [n for n in archive.names if n.startswith("files/")] == [f"files/{real}"]
    assert archive.manifest["files"] == 1
