"""Outils des tests de `account` : deux comptes, leurs lignes et leurs fichiers, l'archive lue."""

import io
import json
import zipfile
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.accounts import ApiKey, AuthSession, User, UserSettingsRow
from app.db.models.agents import LlmCall
from app.db.models.learning import Goal
from app.db.models.memory import MemoryItem
from tests.sessions_support import act_as

API = "/api/v1/account/export"
OTHER = "autre-compte-0000-0000-000000000002"


class Archive:
    """Une archive d'export ouverte : noms, textes décompressés, tables lues."""

    def __init__(self, raw: bytes) -> None:
        self.raw = raw
        self.zip = zipfile.ZipFile(io.BytesIO(raw))
        self.names = self.zip.namelist()

    def read(self, name: str) -> bytes:
        return self.zip.read(name)

    def text(self) -> str:
        """Tout le contenu décompressé (noms compris), pour chercher une valeur partout."""
        parts = [self.read(name).decode("utf-8", "replace") for name in self.names]
        return "\n".join([*self.names, *parts])

    def table(self, name: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = json.loads(self.read(f"tables/{name}.json"))
        return rows

    @property
    def manifest(self) -> dict[str, Any]:
        manifest: dict[str, Any] = json.loads(self.read("manifest.json"))
        return manifest


async def export_archive(client: httpx.AsyncClient) -> Archive:
    response = await client.get(API)
    assert response.status_code == 200, response.text
    return Archive(response.content)


async def seed_user(db: AsyncSession, user_id: str, tag: str, cipher_token: str) -> None:
    """Une ligne de chaque sorte pour `user_id`, toutes marquées de `tag`."""
    db.add_all(
        [
            UserSettingsRow(user_id=user_id, data={"timezone": "Europe/Paris", "note": tag}),
            ApiKey(user_id=user_id, provider="glm", encrypted_key=cipher_token, last4="wxyz"),
            AuthSession(
                user_id=user_id,
                token_hash=f"hash-session-{tag}",
                expires_at=datetime(2030, 1, 1, tzinfo=UTC),
            ),
            LlmCall(user_id=user_id, provider="glm", model=f"modele-{tag}", cost_usd=0.5),
            Goal(user_id=user_id, text=f"objectif-{tag}", framing={"q": [tag]}),
            MemoryItem(
                user_id=user_id,
                kind="fact",
                title=f"titre-{tag}",
                text=f"texte-{tag}",
                created_by="test",
                content_hash=f"hash-{tag}",
            ),
        ]
    )
    await db.commit()


async def seed_other_user(db: AsyncSession) -> None:
    db.add(User(id=OTHER, user_id=OTHER, email="dominique.exemple@example.org", name="Dominique"))
    await db.commit()


def as_other(app: FastAPI) -> None:
    act_as(app, OTHER)
