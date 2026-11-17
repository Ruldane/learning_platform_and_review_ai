from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.db.models.accounts import AuthSession, User
from app.features.auth.service.authenticator import (
    CookieAuthenticator,
    LocalAuthenticator,
    build_authenticator,
)
from app.main import create_app
from tests.features.auth.support import CAMILLE, DOMINIQUE, FakeGoogle, set_cookie, sign_in

ME = "/api/v1/auth/me"
Count = Callable[[], Awaitable[int]]


def is_auth_required(r: httpx.Response) -> bool:
    return (
        r.status_code == 401
        and r.json()["error"]["code"] == "auth_required"
        and r.json()["error"]["message"] == "Connexion requise."
    )


async def test_no_cookie_is_401(google_client: httpx.AsyncClient) -> None:
    assert is_auth_required(await google_client.get(ME))


@pytest.mark.parametrize("value", ["", "garbage", "a" * 5000, "../../etc/passwd"])
async def test_forged_cookie_is_401(google_client: httpx.AsyncClient, value: str) -> None:
    r = await google_client.get(ME, headers={"cookie": f"tremplin_session={value}"})
    assert is_auth_required(r)


async def test_a_real_cookie_of_another_name_does_not_count(
    google_client: httpx.AsyncClient, google: FakeGoogle
) -> None:
    token = set_cookie(await sign_in(google_client, google), "tremplin_session") or ""
    token = token.split(";")[0].split("=", 1)[1]
    google_client.cookies.clear()
    assert is_auth_required(await google_client.get(ME, headers={"cookie": f"other={token}"}))
    assert (await google_client.get(ME, headers={"cookie": f"tremplin_session={token}"})).is_success


async def test_expired_session_is_401(
    google_client: httpx.AsyncClient,
    google: FakeGoogle,
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await sign_in(google_client, google)
    assert (await google_client.get(ME)).status_code == 200
    async with db_session_factory() as db:
        past = datetime.now(UTC) - timedelta(seconds=1)
        await db.execute(update(AuthSession).values(expires_at=past))
        await db.commit()
    assert is_auth_required(await google_client.get(ME))


async def test_deleted_user_cookie_is_401(
    google_client: httpx.AsyncClient,
    google: FakeGoogle,
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await sign_in(google_client, google)
    assert (await google_client.get(ME)).status_code == 200
    async with db_session_factory() as db:
        await db.execute(delete(User))
        await db.commit()
    assert is_auth_required(await google_client.get(ME))


async def test_email_removed_from_allowlist_is_401(
    google_client: httpx.AsyncClient, google: FakeGoogle, google_settings: Settings
) -> None:
    google_settings.allowed_emails = f"{CAMILLE},{DOMINIQUE}"
    await sign_in(google_client, google, CAMILLE)
    assert (await google_client.get(ME)).status_code == 200
    google_settings.allowed_emails = DOMINIQUE  # la requête suivante est déjà refusée
    assert is_auth_required(await google_client.get(ME))
    google_settings.allowed_emails = f"  {CAMILLE.upper()} "  # remise : la même session rouvre
    assert (await google_client.get(ME)).status_code == 200


async def test_each_cookie_is_its_own_account(
    google_client: httpx.AsyncClient, google: FakeGoogle
) -> None:
    a = set_cookie(await sign_in(google_client, google, CAMILLE), "tremplin_session") or ""
    b = set_cookie(await sign_in(google_client, google, DOMINIQUE), "tremplin_session") or ""
    cookie_a, cookie_b = (c.split(";")[0] for c in (a, b))
    google_client.cookies.clear()
    me_a = (await google_client.get(ME, headers={"cookie": cookie_a})).json()
    me_b = (await google_client.get(ME, headers={"cookie": cookie_b})).json()
    assert me_a["email"] == CAMILLE and me_b["email"] == DOMINIQUE and me_a["id"] != me_b["id"]


async def test_protected_routes_need_the_cookie(
    google_client: httpx.AsyncClient, google: FakeGoogle
) -> None:
    assert is_auth_required(await google_client.get("/api/v1/settings"))
    await sign_in(google_client, google)
    assert (await google_client.get("/api/v1/settings")).status_code == 200


async def test_local_authenticator_is_the_single_user() -> None:
    user = await LocalAuthenticator("local-id").authenticate(None)  # type: ignore[arg-type]
    assert (user.id, user.email) == ("local-id", None)


async def test_local_mode_ignores_any_cookie(client: httpx.AsyncClient) -> None:
    r = await client.get(ME, headers={"cookie": "tremplin_session=whatever"})
    assert r.status_code == 200 and r.json()["name"] == "local"


def test_build_authenticator_picks_the_mode(
    settings: Settings,
    google_settings: Settings,
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    assert isinstance(build_authenticator(settings, db_session_factory, "u"), LocalAuthenticator)
    cookie = build_authenticator(google_settings, db_session_factory, None)
    assert isinstance(cookie, CookieAuthenticator)
    with pytest.raises(RuntimeError, match="utilisateur local"):
        build_authenticator(settings, db_session_factory, None)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"google_client_id": None}, "GOOGLE_CLIENT_ID"),
        ({"google_client_id": ""}, "GOOGLE_CLIENT_ID"),
        ({"google_client_secret": None}, "GOOGLE_CLIENT_SECRET"),
        ({"allowed_emails": None}, "ALLOWED_EMAILS est vide"),
        ({"allowed_emails": ""}, "ALLOWED_EMAILS est vide"),
        ({"allowed_emails": " , "}, "ALLOWED_EMAILS est vide"),
        ({"google_token_url": "http://oauth2.example.invalid/token"}, "GOOGLE_TOKEN_URL"),
        ({"google_token_url": "ftp://localhost/token"}, "GOOGLE_TOKEN_URL"),
    ],
)
async def test_google_mode_without_client_id_refuses_to_start(
    google_settings: Settings, db_engine: object, changes: dict[str, object], message: str
) -> None:
    broken = google_settings.model_copy(update=changes)
    with pytest.raises(RuntimeError, match=message) as caught:
        async with LifespanManager(create_app(broken)):
            pass
    assert "test-secret-never-logged" not in str(caught.value)


@pytest.mark.parametrize(
    "token_url",
    [
        "https://oauth2.googleapis.com/token",
        "http://localhost:8000/fake-oidc/token",
        "http://127.0.0.1:8099/token",
    ],
)
async def test_google_mode_starts_with_https_or_a_loopback_token_url(
    google_settings: Settings, db_engine: object, token_url: str
) -> None:
    app: FastAPI = create_app(google_settings.model_copy(update={"google_token_url": token_url}))
    async with LifespanManager(app):
        assert app.state.providers.oidc is not None


async def test_local_mode_needs_no_google_settings(client: httpx.AsyncClient, app: FastAPI) -> None:
    assert app.state.settings.google_client_id is None and app.state.providers.oidc is None
    assert (await client.get(ME)).status_code == 200
