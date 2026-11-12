"""Clé Brave dans l'écran des clés : listée, chiffrée, masquée, testée, isolée par utilisateur,
jamais prise pour un fournisseur LLM."""

import logging
from collections.abc import Callable

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.providers import Providers
from app.db.models.accounts import ApiKey
from app.features.settings.keys_service import ApiKeyService
from tests.features.settings.conftest import VALID_BRAVE_KEY
from tests.sessions_support import act_as

KEYS = "/api/v1/settings/api-keys"
BRAVE_KEY = "BSA-0123456789"


async def _brave(client: httpx.AsyncClient) -> dict[str, object]:
    listed = (await client.get(KEYS)).json()
    return next(k for k in listed if k["provider"] == "brave")


async def test_brave_is_listed_without_a_key(client: httpx.AsyncClient) -> None:
    brave = await _brave(client)
    assert brave["source"] is None and brave["last4"] is None and brave["label"] == "Brave Search"


async def test_brave_key_listed_saved_and_masked(
    client: httpx.AsyncClient, db_session: AsyncSession, providers: Providers
) -> None:
    saved = await client.post(KEYS, json={"provider": "brave", "key": BRAVE_KEY})
    assert saved.status_code == 200 and BRAVE_KEY not in saved.text
    brave = await _brave(client)
    assert brave["last4"] == "6789" and brave["label"] == "Brave Search"
    assert brave["source"] == "ui" and BRAVE_KEY not in str(brave)
    row = (await db_session.execute(select(ApiKey).where(ApiKey.provider == "brave"))).scalar_one()
    assert BRAVE_KEY not in row.encrypted_key
    assert providers.cipher.decrypt(row.encrypted_key) == BRAVE_KEY


async def test_brave_short_key_is_rejected_without_echo(client: httpx.AsyncClient) -> None:
    r = await client.post(KEYS, json={"provider": "brave", "key": "BSA-123"})
    assert r.status_code == 422 and "BSA-123" not in r.text


async def test_brave_key_test_reports_ok_and_refusal(
    client: httpx.AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    await client.post(KEYS, json={"provider": "brave", "key": BRAVE_KEY})
    refused = await client.post(f"{KEYS}/brave/test")
    assert refused.json() == {"ok": False, "message": "Clé refusée par Brave Search."}
    assert (await _brave(client))["last_test_ok"] is False
    await client.post(KEYS, json={"provider": "brave", "key": VALID_BRAVE_KEY})
    assert (await client.post(f"{KEYS}/brave/test")).json()["ok"] is True
    assert BRAVE_KEY not in caplog.text and VALID_BRAVE_KEY not in caplog.text


async def test_brave_key_delete(client: httpx.AsyncClient) -> None:
    await client.post(KEYS, json={"provider": "brave", "key": BRAVE_KEY})
    assert (await client.delete(f"{KEYS}/brave")).status_code == 204
    assert (await _brave(client))["source"] is None


async def test_models_overview_excludes_brave(client: httpx.AsyncClient) -> None:
    await client.post(KEYS, json={"provider": "brave", "key": BRAVE_KEY})
    body = (await client.get("/api/v1/settings/models")).json()
    assert [p["name"] for p in body["providers"]] == ["fake"]


async def test_brave_env_key_is_listed_but_has_no_model_list(
    service_with_env: Callable[[dict[str, str | None]], ApiKeyService],
) -> None:
    service = service_with_env({"brave": "BSA-env-key-9999"})
    with pytest.raises(AppError) as caught:
        await service.list_models("brave")
    assert caught.value.code == "unknown_provider"
    assert await service.get_plaintext("brave") == "BSA-env-key-9999"
    listed = {k.provider: k for k in await service.list()}
    assert listed["brave"].source == "env" and listed["brave"].last4 == "9999"


async def test_brave_key_isolated_between_users(client: httpx.AsyncClient, app: FastAPI) -> None:
    await client.post(KEYS, json={"provider": "brave", "key": BRAVE_KEY})
    act_as(app, "autre-utilisateur")
    assert (await _brave(client))["source"] is None
    tested = await client.post(f"{KEYS}/brave/test")
    assert tested.json()["ok"] is False and "Aucune clé" in tested.json()["message"]
