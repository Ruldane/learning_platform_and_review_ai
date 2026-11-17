from collections.abc import Awaitable, Callable

import httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.features.auth.repository import UserRepository
from tests.features.auth.claim_support import another_browser
from tests.features.auth.support import (
    CAMILLE,
    DOMINIQUE,
    FakeGoogle,
    cookie_value,
    set_cookie,
    sign_in,
)

Count = Callable[[], Awaitable[int]]
ME = "/api/v1/auth/me"
LOGOUT = "/api/v1/auth/logout"


async def test_logout_clears_cookie_and_session(
    google_client: httpx.AsyncClient, google: FakeGoogle, count_sessions: Count
) -> None:
    token = cookie_value(await sign_in(google_client, google), "tremplin_session")
    assert await count_sessions() == 1
    r = await google_client.post(LOGOUT)
    assert r.status_code == 204 and r.content == b""
    cleared = (set_cookie(r, "tremplin_session") or "").lower()
    assert "max-age=0" in cleared and "path=/" in cleared and "httponly" in cleared
    assert "samesite=lax" in cleared and "; secure" not in cleared
    assert await count_sessions() == 0  # la ligne est retirée, pas seulement le cookie
    assert (await google_client.get(ME)).status_code == 401
    # Le jeton rejoué à la main ne rouvre rien : la session n'existe plus côté serveur.
    replay = await google_client.get(ME, headers={"cookie": f"tremplin_session={token}"})
    assert replay.status_code == 401 and replay.json()["error"]["code"] == "auth_required"


async def test_logout_closes_only_its_own_session(
    google_app: FastAPI,
    google_client: httpx.AsyncClient,
    google: FakeGoogle,
    count_sessions: Count,
) -> None:
    await sign_in(google_client, google, CAMILLE)
    async with another_browser(google_app) as second:
        await sign_in(second, google, DOMINIQUE)
        assert await count_sessions() == 2
        assert (await google_client.post(LOGOUT)).status_code == 204
        assert await count_sessions() == 1
        assert (await second.get(ME)).json()["email"] == DOMINIQUE


async def test_logout_without_a_session_is_204(
    google_client: httpx.AsyncClient, count_sessions: Count
) -> None:
    for headers in ({}, {"cookie": "tremplin_session=forged-0000"}):
        r = await google_client.post(LOGOUT, headers=headers)
        assert r.status_code == 204
        assert "max-age=0" in (set_cookie(r, "tremplin_session") or "").lower()
    assert await count_sessions() == 0


async def test_logout_cookie_is_secure_over_https(
    google_client: httpx.AsyncClient,
    google: FakeGoogle,
    google_app: FastAPI,
) -> None:
    await sign_in(google_client, google)
    google_app.state.settings.google_redirect_uri = "https://tremplin.example.org/cb"
    r = await google_client.post(LOGOUT)
    assert "; secure" in (set_cookie(r, "tremplin_session") or "").lower()


async def test_logout_local_mode_is_noop(
    client: httpx.AsyncClient, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    before = (await client.get(ME)).json()
    r = await client.post(LOGOUT, headers={"cookie": "tremplin_session=anything"})
    assert r.status_code == 204 and set_cookie(r, "tremplin_session") is None
    assert (await client.get(ME)).json() == before  # toujours l'utilisateur unique
    async with db_session_factory() as db:
        assert await UserRepository(db).get_local() is not None
