"""Le retour de Google qui tourne mal : toujours une redirection vers `/connexion?erreur=<code>`,
jamais une 500, rien d'écrit, le témoin `tremplin_oauth` effacé (suites de la revue de 9.A2)."""

import logging
from collections.abc import Awaitable, Callable

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import KnownSecrets
from app.db.models.accounts import User
from app.features.auth.service import login
from tests.features.auth.support import (
    CAMILLE,
    DOMINIQUE,
    FakeGoogle,
    failed,
    set_cookie,
    sign_in,
)

Count = Callable[[], Awaitable[int]]


def oauth_cleared(r: httpx.Response) -> bool:
    return "max-age=0" in (set_cookie(r, "tremplin_oauth") or "").lower()


async def test_a_code_already_used_is_token_invalid(
    google_client: httpx.AsyncClient,
    google: FakeGoogle,
    count_users: Count,
    count_sessions: Count,
) -> None:
    google.status = 400  # Google : `invalid_grant`
    r = await sign_in(google_client, google)
    assert r.status_code == 302 and r.headers["location"] == failed("token_invalid")
    assert oauth_cleared(r) and set_cookie(r, "tremplin_session") is None
    assert await count_users() == 0 and await count_sessions() == 0


async def test_a_deeply_nested_token_response_is_token_invalid(
    google_client: httpx.AsyncClient, google: FakeGoogle, count_users: Count
) -> None:
    google.body = b"[" * 100_000  # 200, mais un JSON imbriqué sans fin
    r = await sign_in(google_client, google)
    assert r.status_code == 302 and r.headers["location"] == failed("token_invalid")
    assert oauth_cleared(r) and await count_users() == 0


async def test_an_unexpected_error_redirects_and_undoes_everything(
    google_client: httpx.AsyncClient,
    google: FakeGoogle,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    count_users: Count,
    count_sessions: Count,
) -> None:
    real = login._find_or_create

    async def broken(db: object, users: object, identity: object) -> object:
        await real(db, users, identity)  # type: ignore[arg-type]  # écrit, puis échoue
        raise RuntimeError("detail-never-logged")

    monkeypatch.setattr(login, "_find_or_create", broken)
    caplog.set_level(logging.INFO)
    r = await sign_in(google_client, google)
    assert r.status_code == 302 and r.headers["location"] == failed("token_invalid")
    assert oauth_cleared(r) and set_cookie(r, "tremplin_session") is None
    assert await count_users() == 0 and await count_sessions() == 0  # rien n'est resté écrit
    logged = " ".join(record.getMessage() for record in caplog.records)
    assert "RuntimeError" in logged and "detail-never-logged" not in logged


async def test_a_known_account_whose_new_address_is_taken_is_refused(
    google_client: httpx.AsyncClient,
    google: FakeGoogle,
    db_session_factory: async_sessionmaker[AsyncSession],
    count_sessions: Count,
) -> None:
    await sign_in(google_client, google, CAMILLE, sub="sub-a", name="Camille Exemple")
    await sign_in(google_client, google, DOMINIQUE, sub="sub-b", name="Dominique Exemple")
    before = await count_sessions()
    # Le compte `sub-a` revient avec l'adresse de l'autre : refus, rien de modifié, aucune session.
    r = await sign_in(google_client, google, DOMINIQUE, sub="sub-a", name="Autre Nom")
    assert r.headers["location"] == failed("token_invalid") and oauth_cleared(r)
    assert set_cookie(r, "tremplin_session") is None and await count_sessions() == before
    async with db_session_factory() as db:
        rows = {u.google_sub: u for u in (await db.execute(select(User))).scalars()}
    assert rows["sub-a"].email == CAMILLE and rows["sub-a"].name == "Camille Exemple"
    assert rows["sub-b"].email == DOMINIQUE


async def test_an_address_longer_than_320_characters_is_refused_not_cut(
    google_client: httpx.AsyncClient, google: FakeGoogle, count_users: Count
) -> None:
    r = await sign_in(google_client, google, "a" * 310 + "@example.org")
    assert r.headers["location"] == failed("token_invalid") and await count_users() == 0


async def test_the_client_secret_is_masked_in_logs(google_app: FastAPI) -> None:
    secret = google_app.state.settings.google_client_secret
    assert secret in KnownSecrets.values()
