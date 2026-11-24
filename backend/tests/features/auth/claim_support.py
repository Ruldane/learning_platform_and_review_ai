"""Outils des tests de la reprise de l'espace local : un espace local déjà peuplé, un second
navigateur, le choix de la première connexion. Aucun réseau."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.db.models.accounts import User
from app.db.models.learning import Goal
from app.features.auth.repository import UserRepository
from tests.features.auth.support import CAMILLE, DOMINIQUE, FakeGoogle, set_cookie, sign_in

CLAIM = "/api/v1/auth/google/claim"
GOALS = "/api/v1/goals"
LOCAL_GOAL = "Devenir développeuse back-end"
Factory = async_sessionmaker[AsyncSession]


def named(settings: Settings) -> Settings:
    """`ALLOWED_EMAILS` en liste explicite : seule une personne nommée se voit proposer la
    reprise de l'espace local (avec `*`, jamais)."""
    listed = f"{CAMILLE},{DOMINIQUE}"
    return settings.model_copy(update={"allowed_emails": listed})


async def users(factory: Factory) -> list[User]:
    async with factory() as db:
        return list((await db.execute(select(User).order_by(User.created_at))).scalars())


def error_code(r: httpx.Response) -> str:
    assert r.status_code == 409, r.text
    return str(r.json()["error"]["code"])


async def seed_local_space(factory: async_sessionmaker[AsyncSession]) -> str:
    """L'espace créé en mode local : l'utilisateur `local` et un objectif. Rend son `id`."""
    async with factory() as db:
        local = await UserRepository(db).add_local()
        db.add(Goal(user_id=local.id, text=LOCAL_GOAL))
        await db.commit()
        return local.id


@asynccontextmanager
async def another_browser(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    """Un second navigateur (ses propres cookies) sur la même application."""
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def offered(
    client: httpx.AsyncClient, google: FakeGoogle, email: str, **identity: Any
) -> httpx.Response:
    """Une connexion qui doit aboutir au choix de la reprise (et rien d'autre)."""
    r = await sign_in(client, google, email, **identity)
    assert r.headers["location"].endswith("/login/claim"), r.headers["location"]
    assert set_cookie(r, "tremplin_claim") and not set_cookie(r, "tremplin_session")
    return r


async def choose(client: httpx.AsyncClient, choice: str) -> httpx.Response:
    return await client.post(CLAIM, json={"choice": choice})


async def goal_texts(client: httpx.AsyncClient) -> list[str]:
    r = await client.get(GOALS)
    assert r.status_code == 200, r.text
    return [goal["text"] for goal in r.json()]
