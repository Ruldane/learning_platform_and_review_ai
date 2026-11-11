import httpx
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Db
from app.db.models.accounts import User


def _add_routes(app: FastAPI) -> None:
    @app.post("/api/v1/_users/{email}")
    async def create(email: str, db: Db) -> None:
        db.add(User(id="u1", user_id="u1", email=email))

    @app.post("/api/v1/_users_fail")
    async def create_then_fail(db: Db) -> None:
        db.add(User(id="u2", user_id="u2", email="b@x.test"))
        await db.flush()
        raise RuntimeError("échec après écriture")


async def test_commit_failure_is_an_error_response_not_a_200(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    @app.post("/api/v1/_commit_fails")
    async def commit_fails(db: Db) -> dict[str, bool]:
        async def broken_commit() -> None:
            raise RuntimeError("commit impossible")

        db.commit = broken_commit  # type: ignore[method-assign]
        return {"ok": True}

    r = await client.post("/api/v1/_commit_fails")
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "internal_error"


async def test_get_db_commits_and_client_sees_same_data(
    app: FastAPI, client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    _add_routes(app)
    assert (await client.post("/api/v1/_users/a@x.test")).status_code == 200
    # L'utilisateur local (sans e-mail) est créé au démarrage : on ne regarde que la ligne écrite.
    users = (await db_session.execute(select(User).where(User.id == "u1"))).scalars().all()
    assert [u.email for u in users] == ["a@x.test"]


async def test_get_db_rolls_back_on_error(
    app: FastAPI, client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    _add_routes(app)
    assert (await client.post("/api/v1/_users_fail")).status_code == 500
    assert (await db_session.execute(select(User).where(User.id == "u2"))).scalars().all() == []


async def test_lifespan_exposes_engine_and_session_factory(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    assert app.state.engine is not None
    assert app.state.session_factory is not None
