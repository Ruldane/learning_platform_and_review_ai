import json
import time
from collections.abc import Awaitable, Callable

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.core.security import load_or_create_secret
from app.db.models.accounts import User
from tests.features.auth.support import (
    CAMILLE,
    DOMINIQUE,
    FRONT,
    FakeGoogle,
    come_back,
    cookie_value,
    failed,
    location_query,
    set_cookie,
    sign_in,
    start,
)

Count = Callable[[], Awaitable[int]]


async def test_callback_signs_in_and_sets_30_day_cookie(
    google_client: httpx.AsyncClient, google: FakeGoogle, count_users: Count, count_sessions: Count
) -> None:
    r = await sign_in(google_client, google)
    assert r.status_code == 302 and r.headers["location"] == f"{FRONT}/"
    cookie = set_cookie(r, "tremplin_session")
    assert cookie is not None
    low = cookie.lower()
    assert "httponly" in low and "samesite=lax" in low and "max-age=2592000" in low
    assert "path=/" in low and "; secure" not in low
    # Le témoin de la connexion est effacé, au même chemin que la pose.
    cleared = set_cookie(r, "tremplin_oauth")
    assert cleared is not None and "max-age=0" in cleared.lower()
    assert "path=/api/v1/auth/google" in cleared.lower()
    assert await count_users() == 1 and await count_sessions() == 1


async def test_session_cookie_is_secure_over_https(
    google_client: httpx.AsyncClient, google: FakeGoogle, google_app: FastAPI
) -> None:
    # Départ en http (le client de test n'enverrait pas un témoin `Secure`), retour en https.
    query = location_query(await start(google_client))
    google.nonce = query["nonce"]
    google_app.state.settings.google_redirect_uri = "https://tremplin.example.org/cb"
    r = await come_back(google_client, code="c", state=query["state"])
    cookie = set_cookie(r, "tremplin_session")
    assert cookie is not None and "; secure" in cookie.lower()
    assert "; secure" in (set_cookie(r, "tremplin_oauth") or "").lower()


async def test_me_with_cookie_returns_google_user(
    google_client: httpx.AsyncClient, google: FakeGoogle
) -> None:
    await sign_in(google_client, google, "Camille.Exemple@Example.org")
    me = (await google_client.get("/api/v1/auth/me")).json()
    assert me["email"] == CAMILLE and me["name"] == "Camille Exemple"
    assert me["auth_mode"] == "google" and len(me["id"]) == 36


async def test_exchange_sends_the_verifier_of_the_cookie(
    google_client: httpx.AsyncClient, google: FakeGoogle, google_app: FastAPI
) -> None:
    started = await start(google_client)
    query = location_query(started)
    google.nonce = query["nonce"]
    verifier = json.loads(google_app.state.cipher.decrypt(cookie_value(started, "tremplin_oauth")))[
        "verifier"
    ]
    await come_back(google_client, code="the-code", state=query["state"])
    assert google.forms[0]["code"] == "the-code" and google.forms[0]["code_verifier"] == verifier


async def test_state_mismatch_creates_nothing(
    google_client: httpx.AsyncClient, google: FakeGoogle, count_users: Count, count_sessions: Count
) -> None:
    query = location_query(await start(google_client))
    google.nonce = query["nonce"]
    r = await come_back(google_client, code="c", state="forged-state")
    assert r.status_code == 302 and r.headers["location"] == failed("state_invalid")
    assert set_cookie(r, "tremplin_session") is None
    cleared = set_cookie(r, "tremplin_oauth")
    assert cleared is not None and "max-age=0" in cleared.lower()
    assert await count_users() == 0 and await count_sessions() == 0 and google.forms == []


async def test_callback_without_oauth_cookie_is_refused(google_client: httpx.AsyncClient) -> None:
    r = await come_back(google_client, code="c", state="s")
    assert r.status_code == 302 and r.headers["location"] == failed("state_invalid")


async def test_stale_oauth_cookie_refused(
    google_client: httpx.AsyncClient,
    google: FakeGoogle,
    google_settings: Settings,
    count_users: Count,
) -> None:
    fernet = Fernet(load_or_create_secret(google_settings.secret_path))
    pending = json.dumps({"state": "st", "verifier": "v" * 50, "nonce": "n"}).encode()
    stale = fernet.encrypt_at_time(pending, int(time.time()) - 11 * 60).decode()
    fresh = fernet.encrypt_at_time(pending, int(time.time()) - 5 * 60).decode()
    old = await google_client.get(
        "/api/v1/auth/google/callback",
        params={"code": "c", "state": "st"},
        headers={"cookie": f"tremplin_oauth={stale}"},
    )
    assert old.headers["location"] == failed("state_invalid") and google.forms == []
    # Même témoin, de 5 minutes : il passe jusqu'à l'échange (nonce faux, donc refusé plus loin).
    ok = await google_client.get(
        "/api/v1/auth/google/callback",
        params={"code": "c", "state": "st"},
        headers={"cookie": f"tremplin_oauth={fresh}"},
    )
    assert len(google.forms) == 1 and ok.headers["location"] == failed("token_invalid")
    assert await count_users() == 0


@pytest.mark.parametrize("cookie", ["garbage", "gAAAAAB-not-a-real-token"])
async def test_forged_oauth_cookie_is_state_invalid(
    google_client: httpx.AsyncClient, cookie: str
) -> None:
    r = await google_client.get(
        "/api/v1/auth/google/callback",
        params={"code": "c", "state": "s"},
        headers={"cookie": f"tremplin_oauth={cookie}"},
    )
    assert r.status_code == 302 and r.headers["location"] == failed("state_invalid")


async def test_the_code_is_needed(google_client: httpx.AsyncClient) -> None:
    query = location_query(await start(google_client))
    r = await come_back(google_client, state=query["state"])
    assert r.headers["location"] == failed("token_invalid")


async def test_access_denied_redirects(
    google_client: httpx.AsyncClient, count_users: Count, count_sessions: Count
) -> None:
    query = location_query(await start(google_client))
    r = await come_back(google_client, error="access_denied", state=query["state"])
    assert r.status_code == 302 and r.headers["location"] == failed("access_denied")
    assert await count_users() == 0 and await count_sessions() == 0


async def test_unverified_email_refused(
    google_client: httpx.AsyncClient, google: FakeGoogle, count_users: Count
) -> None:
    google.verified = False
    r = await sign_in(google_client, google)
    assert r.headers["location"] == failed("email_unverified") and await count_users() == 0
    assert set_cookie(r, "tremplin_session") is None


async def test_wrong_nonce_refused(
    google_client: httpx.AsyncClient, google: FakeGoogle, count_users: Count
) -> None:
    google.claims = {"nonce": "replayed-from-another-login"}
    r = await sign_in(google_client, google)
    assert r.headers["location"] == failed("token_invalid") and await count_users() == 0


async def test_token_for_another_audience_refused(
    google_client: httpx.AsyncClient, google: FakeGoogle, count_users: Count
) -> None:
    google.claims = {"aud": "someone-else.apps.example.invalid"}
    r = await sign_in(google_client, google)
    assert r.headers["location"] == failed("token_invalid") and await count_users() == 0


async def test_token_endpoint_down_is_readable(
    google_client: httpx.AsyncClient, google: FakeGoogle, count_users: Count
) -> None:
    google.down = True
    r = await sign_in(google_client, google)
    assert r.status_code == 302 and r.headers["location"] == failed("google_unavailable")
    assert await count_users() == 0


async def test_email_not_allowed_creates_nothing(
    google_client: httpx.AsyncClient,
    google: FakeGoogle,
    google_settings: Settings,
    count_users: Count,
    count_sessions: Count,
) -> None:
    google_settings.allowed_emails = DOMINIQUE
    r = await sign_in(google_client, google, CAMILLE)
    assert r.headers["location"] == failed("email_not_allowed")
    assert await count_users() == 0 and await count_sessions() == 0
    assert set_cookie(r, "tremplin_session") is None
    # Une adresse de la liste passe, quelle que soit la casse ou les espaces de la liste.
    google_settings.allowed_emails = f" Autre@Example.org , {DOMINIQUE.upper()} "
    r = await sign_in(google_client, google, DOMINIQUE)
    assert r.headers["location"] == f"{FRONT}/" and await count_users() == 1


async def test_star_accepts_every_account(
    google_client: httpx.AsyncClient,
    google: FakeGoogle,
    google_settings: Settings,
    count_users: Count,
) -> None:
    google_settings.allowed_emails = "*"
    for email in (CAMILLE, DOMINIQUE, "inconnue@example.invalid"):
        r = await sign_in(google_client, google, email)
        assert r.headers["location"] == f"{FRONT}/"
    assert await count_users() == 3


async def test_returning_user_matched_by_sub_updates_email(
    google_client: httpx.AsyncClient,
    google: FakeGoogle,
    db_session_factory: async_sessionmaker[AsyncSession],
    count_users: Count,
) -> None:
    await sign_in(google_client, google, CAMILLE, sub="sub-fixed", name="Camille Exemple")
    first = (await google_client.get("/api/v1/auth/me")).json()
    await sign_in(google_client, google, "Camille.Nouvelle@Example.org", sub="sub-fixed", name="CN")
    again = (await google_client.get("/api/v1/auth/me")).json()
    assert again["id"] == first["id"] and again["email"] == "camille.nouvelle@example.org"
    assert again["name"] == "CN" and await count_users() == 1
    async with db_session_factory() as db:
        user = (await db.execute(select(User))).scalar_one()
        assert user.google_sub == "sub-fixed" and user.user_id == user.id
