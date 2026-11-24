import hashlib
from collections.abc import Awaitable, Callable

import httpx
import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.accounts import AuthSession
from app.features.auth.service.login import CallbackOutcome
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


async def test_email_held_by_another_account_creates_nothing(
    google_client: httpx.AsyncClient, google: FakeGoogle, count_users: Count
) -> None:
    await sign_in(google_client, google, CAMILLE, sub="sub-a")
    r = await sign_in(google_client, google, CAMILLE, sub="sub-b")
    assert r.status_code == 302 and r.headers["location"] == failed("token_invalid")
    assert await count_users() == 1


async def test_only_hash_of_token_stored(
    google_client: httpx.AsyncClient,
    google: FakeGoogle,
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    token = cookie_value(await sign_in(google_client, google), "tremplin_session")
    assert len(token) >= 43
    async with db_session_factory() as db:
        row = (await db.execute(select(AuthSession))).scalar_one()
        assert row.token_hash == hashlib.sha256(token.encode()).hexdigest()
        stored = [str(getattr(row, column.name)) for column in AuthSession.__table__.columns]
        assert all(token not in value for value in stored)
        days = (row.expires_at - row.created_at).total_seconds() / 86400
        assert 29.99 < days < 30.01


async def test_a_new_login_purges_the_expired_sessions_of_that_user_only(
    google_client: httpx.AsyncClient,
    google: FakeGoogle,
    db_session_factory: async_sessionmaker[AsyncSession],
    count_sessions: Count,
) -> None:
    await sign_in(google_client, google, CAMILLE)
    await sign_in(google_client, google, DOMINIQUE)
    assert await count_sessions() == 2
    async with db_session_factory() as db:
        await db.execute(update(AuthSession).values(expires_at=AuthSession.created_at))
        await db.commit()
    await sign_in(google_client, google, CAMILLE)
    # Celle de Camille (expirée) est partie et une neuve est née ; celle de Dominique (expirée
    # aussi) reste : seules les sessions de l'utilisatrice qui se connecte sont purgées.
    assert await count_sessions() == 2


@pytest.mark.parametrize(
    "params",
    [{"code": "c" * 2049, "state": "s"}, {"code": "c", "state": "s" * 2049}, {"error": "e" * 257}],
)
async def test_too_long_callback_parameters_redirect_instead_of_a_422(
    google_client: httpx.AsyncClient, google: FakeGoogle, count_users: Count, params: dict[str, str]
) -> None:
    query = location_query(await start(google_client))
    google.nonce = query["nonce"]
    r = await come_back(google_client, **params)
    assert r.status_code == 302 and r.headers["location"] == failed("state_invalid")
    assert set_cookie(r, "tremplin_session") is None and google.forms == []
    assert set_cookie(r, "tremplin_oauth") is not None and await count_users() == 0


async def test_the_longest_allowed_parameters_still_work(
    google_client: httpx.AsyncClient,
) -> None:
    r = await come_back(google_client, code="c" * 2048, state="s" * 2048)
    assert r.status_code == 302 and r.headers["location"] == failed("state_invalid")
    r = await come_back(google_client, error="e" * 256)
    assert r.headers["location"] == failed("access_denied")


async def test_the_callback_never_follows_a_return_address_parameter(
    google_client: httpx.AsyncClient, google: FakeGoogle
) -> None:
    query = location_query(await start(google_client))
    google.nonce = query["nonce"]
    r = await come_back(
        google_client,
        code="c",
        state=query["state"],
        redirect_uri="https://evil.example.invalid/",
        next="https://evil.example.invalid/",
    )
    assert r.headers["location"].startswith(FRONT)
    assert "evil" not in r.headers["location"]


async def test_a_claim_outcome_sets_the_claim_cookie(
    google_client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # La reprise de l'espace local (9.A3) fournit ce résultat ; le callback sait déjà l'honorer.
    async def claim(*args: object, **kwargs: object) -> CallbackOutcome:
        return CallbackOutcome(kind="claim", claim_cookie="sealed-claim")

    monkeypatch.setattr("app.features.auth.router.finish_login", claim)
    r = await come_back(google_client, code="c", state="s")
    assert r.headers["location"] == f"{FRONT}/login/claim"
    cookie = (set_cookie(r, "tremplin_claim") or "").lower()
    assert "path=/api/v1/auth/google" in cookie and "max-age=600" in cookie
    assert "httponly" in cookie and set_cookie(r, "tremplin_session") is None
