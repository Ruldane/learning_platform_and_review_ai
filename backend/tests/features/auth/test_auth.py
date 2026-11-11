import httpx
import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.models.accounts import User
from app.features.auth.service import AuthService
from app.main import create_app


async def _count_users(session: AsyncSession) -> int:
    return (await session.execute(select(func.count()).select_from(User))).scalar_one()


async def test_ensure_local_user_is_idempotent(db_session: AsyncSession) -> None:
    a = await AuthService(db_session).ensure_local_user()
    b = await AuthService(db_session).ensure_local_user()
    assert a.id == b.id and await _count_users(db_session) == 1
    assert a.user_id == a.id and a.name == "local" and a.email is None


async def test_me_returns_local_user(client: httpx.AsyncClient) -> None:
    r = await client.get("/api/v1/auth/me")
    body = r.json()
    assert r.status_code == 200 and body["auth_mode"] == "local" and body["name"] == "local"
    assert body["email"] is None and len(body["id"]) == 36


async def test_lifespan_stores_local_user_id(app: FastAPI, client: httpx.AsyncClient) -> None:
    first = (await client.get("/api/v1/auth/me")).json()["id"]
    assert app.state.local_user_id == first


async def test_google_mode_requires_login(client_google_mode: httpx.AsyncClient) -> None:
    r = await client_google_mode.get("/api/v1/auth/me")
    assert r.status_code == 401 and r.json()["error"]["code"] == "auth_required"
    assert r.json()["error"]["message"] == "Connexion requise."


async def test_startup_fails_clearly_when_schema_is_missing(settings: Settings) -> None:
    # Pas de `db_engine` : la base est vide, le lifespan doit échouer avec un message français.
    with pytest.raises(RuntimeError, match="alembic upgrade head"):
        async with LifespanManager(create_app(settings)):
            pass
