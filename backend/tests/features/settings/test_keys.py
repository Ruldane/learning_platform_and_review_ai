import logging
from collections.abc import Callable

import httpx
import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import AppError
from app.core.providers import Providers
from app.core.security import Cipher, KnownSecrets, SecretUnreadable
from app.db.models.accounts import ApiKey
from app.features.settings.keys_service import ApiKeyService, DbKeyReader
from tests.features.settings.conftest import USER_ID, ListingProvider

SECRET = "fake-key-ABCDEFGH1234"
KEYS = "/api/v1/settings/api-keys"
Svc = Callable[[dict[str, str | None]], ApiKeyService]


async def get_api_key_row(session: AsyncSession, provider: str) -> ApiKey:
    stmt = select(ApiKey).where(ApiKey.provider == provider)
    return (await session.execute(stmt)).scalar_one()


async def _entry(client: httpx.AsyncClient, provider: str = "fake") -> dict[str, object]:
    return next(e for e in (await client.get(KEYS)).json() if e["provider"] == provider)


async def test_saved_key_is_never_returned(client: httpx.AsyncClient) -> None:
    r = await client.post(KEYS, json={"provider": "fake", "key": SECRET})
    listed = await client.get(KEYS)
    assert SECRET not in r.text and SECRET not in listed.text
    entry = next(e for e in listed.json() if e["provider"] == "fake")
    assert entry["last4"] == "1234" and entry["source"] == "ui" and entry["readable"] is True
    assert entry["label"] == "Faux fournisseur"


async def test_key_is_encrypted_at_rest(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await client.post(KEYS, json={"provider": "fake", "key": SECRET})
    row = await get_api_key_row(db_session, "fake")
    assert row.encrypted_key != SECRET and SECRET not in row.encrypted_key
    assert row.last4 == "1234"


async def test_test_endpoint_reports_ok_and_failure(client: httpx.AsyncClient) -> None:
    await client.post(KEYS, json={"provider": "fake", "key": "fake-key"})
    assert (await client.post(f"{KEYS}/fake/test")).json()["ok"] is True
    await client.post(KEYS, json={"provider": "fake", "key": "mauvaise"})
    r = await client.post(f"{KEYS}/fake/test")
    assert r.json()["ok"] is False and "mauvaise" not in r.text


async def test_test_result_is_recorded(client: httpx.AsyncClient) -> None:
    await client.post(KEYS, json={"provider": "fake", "key": "fake-key"})
    before = await _entry(client)
    assert before["last_tested_at"] is None and before["last_test_ok"] is None
    await client.post(f"{KEYS}/fake/test")
    after = await _entry(client)
    assert after["last_test_ok"] is True and after["last_tested_at"] is not None
    await client.post(KEYS, json={"provider": "fake", "key": "mauvaise"})
    await client.post(f"{KEYS}/fake/test")
    assert (await _entry(client))["last_test_ok"] is False


async def test_replacing_a_key_resets_its_test_result(client: httpx.AsyncClient) -> None:
    await client.post(KEYS, json={"provider": "fake", "key": "fake-key"})
    await client.post(f"{KEYS}/fake/test")
    await client.post(KEYS, json={"provider": "fake", "key": "autre-clef"})
    entry = await _entry(client)
    assert entry["last_tested_at"] is None and entry["last_test_ok"] is None


async def test_test_without_key_is_a_result_not_an_error(client: httpx.AsyncClient) -> None:
    r = await client.post(f"{KEYS}/fake/test")
    assert r.status_code == 200
    assert r.json() == {"ok": False, "message": "Aucune clé enregistrée pour Faux fournisseur."}


async def test_ui_key_wins_over_env(service_with_env: Svc) -> None:
    svc = service_with_env({"fake": "env-key"})
    assert await svc.get_plaintext("fake") == "env-key"
    await svc.set("fake", "ui-key-123")
    assert await svc.get_plaintext("fake") == "ui-key-123"


async def test_env_key_is_listed_with_source_env(service_with_env: Svc) -> None:
    svc = service_with_env({"fake": "env-key-ZZZ9"})
    (entry,) = await svc.list()
    assert entry.source == "env" and entry.last4 == "ZZZ9" and entry.readable is True
    await svc.delete("fake")  # rien en base : sans effet, la clé .env reste
    assert await svc.get_plaintext("fake") == "env-key-ZZZ9"


async def test_nothing_configured(service_with_env: Svc) -> None:
    svc = service_with_env({"fake": None})
    (entry,) = await svc.list()
    assert entry.source is None and entry.last4 is None and entry.readable is True
    assert await svc.get_plaintext("fake") is None


async def test_blank_env_key_counts_as_absent(service_with_env: Svc) -> None:
    assert await service_with_env({"fake": "  "}).get_plaintext("fake") is None


async def test_delete_removes_ui_key_and_is_idempotent(client: httpx.AsyncClient) -> None:
    await client.post(KEYS, json={"provider": "fake", "key": SECRET})
    assert (await client.delete(f"{KEYS}/fake")).status_code == 204
    assert (await client.delete(f"{KEYS}/fake")).status_code == 204
    entry = await _entry(client)
    assert entry["source"] is None and entry["last4"] is None


async def test_regenerated_secret_marks_key_unreadable(
    client: httpx.AsyncClient, swap_cipher: Callable[[], None]
) -> None:
    await client.post(KEYS, json={"provider": "fake", "key": SECRET})
    swap_cipher()  # nouveau secret : la clé stockée n'est plus déchiffrable
    r = await client.get(KEYS)
    assert r.status_code == 200
    entry = next(e for e in r.json() if e["provider"] == "fake")
    assert entry["readable"] is False and entry["last4"] == "1234" and entry["source"] == "ui"
    tested = await client.post(f"{KEYS}/fake/test")
    assert tested.status_code == 200 and tested.json()["ok"] is False
    # Ressaisir la clé la rend de nouveau lisible.
    await client.post(KEYS, json={"provider": "fake", "key": SECRET})
    assert (await _entry(client))["readable"] is True


async def test_unreadable_key_raises_in_service(
    service_with_env: Svc, swap_cipher: Callable[[], None]
) -> None:
    await service_with_env({}).set("fake", SECRET)
    swap_cipher()
    with pytest.raises(SecretUnreadable):
        await service_with_env({"fake": "env-key"}).get_plaintext("fake")


async def test_key_never_logged(
    client: httpx.AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    await client.post(KEYS, json={"provider": "fake", "key": SECRET})
    await client.post(f"{KEYS}/fake/test")
    await client.get("/api/v1/settings/models")
    assert SECRET not in caplog.text


async def test_saved_key_is_registered_for_log_masking(client: httpx.AsyncClient) -> None:
    secret = "masquer-moi-9876543"
    await client.post(KEYS, json={"provider": "fake", "key": secret})
    assert secret in KnownSecrets.values()


async def test_unknown_provider_is_404(client: httpx.AsyncClient) -> None:
    r = await client.post(f"{KEYS}/nope/test")
    assert r.status_code == 404 and r.json()["error"]["code"] == "unknown_provider"
    assert r.json()["error"]["message"] == "Fournisseur inconnu : nope."
    assert (await client.delete(f"{KEYS}/nope")).status_code == 404
    posted = await client.post(KEYS, json={"provider": "nope", "key": SECRET})
    assert posted.status_code == 404 and SECRET not in posted.text


@pytest.mark.parametrize("key", ["", "   ", "\n"])
async def test_empty_key_is_422(client: httpx.AsyncClient, key: str) -> None:
    r = await client.post(KEYS, json={"provider": "fake", "key": key})
    assert r.status_code == 422 and "code" in r.json()["error"]


async def test_short_key_is_422_and_not_echoed(client: httpx.AsyncClient) -> None:
    r = await client.post(KEYS, json={"provider": "fake", "key": "abc1234"})
    assert r.status_code == 422
    assert r.json()["error"] == {
        "code": "invalid_key",
        "message": "La clé est trop courte.",
        "details": None,
    }
    assert "abc1234" not in r.text


@pytest.mark.parametrize(
    "body",
    [
        {"key": "SUPERSECRETKEY1234"},
        {"provider": "fake", "key": ["SUPERSECRETKEY1234"]},
        {"provider": ["fake"], "key": "SUPERSECRETKEY1234"},
    ],
)
async def test_malformed_body_never_echoes_the_key(
    client: httpx.AsyncClient, body: dict[str, object]
) -> None:
    r = await client.post(KEYS, json=body)
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
    assert "SUPERSECRETKEY1234" not in r.text


async def test_service_list_models(
    service_with_env: Svc, providers: Providers, swap_cipher: Callable[[], None]
) -> None:
    providers.llm = {"fake": ListingProvider(["m-1", "m-2"])}
    svc = service_with_env({})
    assert await svc.list_models("fake") is None  # pas de clé
    await svc.set("fake", SECRET)
    assert await svc.list_models("fake") == ["m-1", "m-2"]
    swap_cipher()
    assert await service_with_env({}).list_models("fake") is None  # clé illisible
    with pytest.raises(AppError):
        await svc.list_models("nope")


async def test_key_is_stripped_before_storing(
    client: httpx.AsyncClient, db_session: AsyncSession, providers: Providers
) -> None:
    await client.post(KEYS, json={"provider": "fake", "key": f"  {SECRET}\n"})
    assert (await _entry(client))["last4"] == "1234"
    row = await get_api_key_row(db_session, "fake")
    assert providers.cipher.decrypt(row.encrypted_key) == SECRET


async def test_keys_are_isolated_per_user(providers: Providers, db_session: AsyncSession) -> None:
    one = ApiKeyService(db_session, "u1", providers.cipher, {}, providers.llm)
    two = ApiKeyService(db_session, "u2", providers.cipher, {}, providers.llm)
    await one.set("fake", SECRET)
    assert await two.get_plaintext("fake") is None
    assert await one.get_plaintext("fake") == SECRET


async def test_db_key_reader_follows_the_same_priority(
    db_session_factory: async_sessionmaker[AsyncSession],
    providers: Providers,
    db_session: AsyncSession,
) -> None:
    env: dict[str, str | None] = {"fake": "env-key-0001"}
    reader = DbKeyReader(db_session_factory, providers.cipher, env)
    assert await reader.get_key(USER_ID, "fake") == "env-key-0001"
    assert await reader.get_key(USER_ID, "other") is None
    service = ApiKeyService(db_session, USER_ID, providers.cipher, env, providers.llm)
    await service.set("fake", "ui-key-0002")
    await db_session.commit()
    assert await reader.get_key(USER_ID, "fake") == "ui-key-0002"
    other = DbKeyReader(db_session_factory, Cipher(Fernet.generate_key()), env)
    with pytest.raises(SecretUnreadable):
        await other.get_key(USER_ID, "fake")


async def test_models_endpoint_lists_presets(client: httpx.AsyncClient) -> None:
    body = (await client.get("/api/v1/settings/models")).json()
    assert set(body["presets"]) == {"all_haiku", "haiku_sonnet_strong", "all_glm", "all_openai"}
    assert body["presets"]["all_glm"]["fort"]["provider"] == "glm"
    assert body["providers"] == [
        {"name": "fake", "label": "Faux fournisseur", "has_key": False, "models": None}
    ]


async def test_models_endpoint_lists_models_only_with_a_key(
    client: httpx.AsyncClient, providers: Providers
) -> None:
    providers.llm = {"fake": ListingProvider(["m-1", "m-2"])}
    first = (await client.get("/api/v1/settings/models")).json()["providers"][0]
    assert first["has_key"] is False and first["models"] is None
    await client.post(KEYS, json={"provider": "fake", "key": SECRET})
    second = (await client.get("/api/v1/settings/models")).json()["providers"][0]
    assert second["has_key"] is True and second["models"] == ["m-1", "m-2"]


async def test_models_provider_error_does_not_fail_the_endpoint(
    client: httpx.AsyncClient, providers: Providers, caplog: pytest.LogCaptureFixture
) -> None:
    good, broken = ListingProvider(["m-1"]), ListingProvider(None, fail=True)
    broken.name, broken.label = "broken", "Cassé"
    providers.llm = {"fake": good, "broken": broken}
    await client.post(KEYS, json={"provider": "fake", "key": SECRET})
    await client.post(KEYS, json={"provider": "broken", "key": "broken-key-5555"})
    r = await client.get("/api/v1/settings/models")
    assert r.status_code == 200
    by_name = {p["name"]: p for p in r.json()["providers"]}
    assert by_name["fake"]["models"] == ["m-1"]
    assert by_name["broken"]["has_key"] is True and by_name["broken"]["models"] is None
    assert "broken-key-5555" not in caplog.text and "broken-key-5555" not in r.text


async def test_models_unreadable_key_has_no_models(
    client: httpx.AsyncClient, providers: Providers, swap_cipher: Callable[[], None]
) -> None:
    providers.llm = {"fake": ListingProvider(["m-1"])}
    await client.post(KEYS, json={"provider": "fake", "key": SECRET})
    swap_cipher()
    r = await client.get("/api/v1/settings/models")
    assert r.status_code == 200
    assert r.json()["providers"][0]["has_key"] is False
    assert r.json()["providers"][0]["models"] is None
