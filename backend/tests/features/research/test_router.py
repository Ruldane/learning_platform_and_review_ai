from dataclasses import dataclass, field

import httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.research import Source
from app.features.research.service.runtime import ResearchRuntime
from tests.features.research.conftest import Clock, seed_brave_usage

Factory = async_sessionmaker[AsyncSession]


@dataclass
class FakeKeys:
    """`KeyReader` factice : utilisateur → clé Brave."""

    brave: dict[str, str] = field(default_factory=dict)

    async def get_key(self, user_id: str, provider: str) -> str | None:
        return self.brave.get(user_id) if provider == "brave" else None


def _research(app: FastAPI, keys: FakeKeys, clock: Clock) -> str:
    """Branche les fausses clés et l'horloge sur la recherche ouverte par le lifespan ; rend
    l'id de l'utilisateur local."""
    research: ResearchRuntime = app.state.research
    research.keys = keys
    research.now = clock
    user_id: str = app.state.local_user_id
    return user_id


async def test_usage_route_counts_current_month(
    client: httpx.AsyncClient, app: FastAPI, clock: Clock, db_session_factory: Factory
) -> None:
    keys = FakeKeys()
    me = _research(app, keys, clock)
    r = await client.get("/api/v1/research/usage")
    assert r.status_code == 200
    assert r.json() == {"brave": {"has_key": False, "used": 0, "cap": 900, "month": "2026-11"}}
    keys.brave[me] = "cle-a"
    await seed_brave_usage(db_session_factory, 7, user_id=me, api_key="cle-a")
    await seed_brave_usage(db_session_factory, 3, user_id="autre", api_key="cle-a")  # même clé
    await seed_brave_usage(db_session_factory, 50, user_id=me, api_key="cle-a", month="2026-10")
    body = (await client.get("/api/v1/research/usage")).json()["brave"]
    assert body == {"has_key": True, "used": 10, "cap": 900, "month": "2026-11"}


async def test_usage_route_isolated_between_users(
    client: httpx.AsyncClient, app: FastAPI, clock: Clock, db_session_factory: Factory
) -> None:
    keys = FakeKeys({"autre": "cle-b"})
    _research(app, keys, clock)
    await seed_brave_usage(db_session_factory, 500, user_id="autre", api_key="cle-b")
    body = (await client.get("/api/v1/research/usage")).json()["brave"]
    assert body["has_key"] is False and body["used"] == 0  # la clé et l'usage d'un autre


async def test_sources_route_lists_session_sources_and_is_isolated(
    client: httpx.AsyncClient, app: FastAPI, db_session_factory: Factory
) -> None:
    me: str = app.state.local_user_id
    async with db_session_factory() as session:
        for user_id, session_id, name in [
            (me, "s1", "a"),
            (me, "s2", "x"),
            ("autre", "s1", "intrus"),
            (me, "s1", "b"),
        ]:
            session.add(
                Source(
                    user_id=user_id,
                    session_id=session_id,
                    url=f"https://ex.org/{name}",
                    url_hash=name,
                    title=name,
                    status="ok",
                )
            )
        await session.commit()
    r = await client.get("/api/v1/research/sources", params={"session_id": "s1"})
    assert r.status_code == 200
    body = r.json()
    assert [s["title"] for s in body] == ["a", "b"]
    assert set(body[0]) == {
        "id",
        "url",
        "title",
        "author",
        "lang",
        "published",
        "status",
        "verdict",
        "score",
        "reason",
        "kind",
    }
    assert body[0]["verdict"] == "pending" and body[0]["score"] is None
    empty = await client.get("/api/v1/research/sources", params={"session_id": "s9"})
    assert empty.json() == []
    missing = await client.get("/api/v1/research/sources")
    assert missing.status_code == 422


async def test_sources_route_exposes_kind(
    client: httpx.AsyncClient, app: FastAPI, db_session_factory: Factory
) -> None:
    me: str = app.state.local_user_id
    async with db_session_factory() as session:
        for name, kind in [("page", "page"), ("ada", "person")]:
            session.add(
                Source(
                    user_id=me,
                    session_id="s1",
                    kind=kind,
                    url=f"https://ex.org/{name}",
                    url_hash=name,
                    title=name,
                    status="ok",
                )
            )
        await session.commit()
    body = (await client.get("/api/v1/research/sources", params={"session_id": "s1"})).json()
    assert [(s["title"], s["kind"]) for s in body] == [("page", "page"), ("ada", "person")]


async def test_research_routes_require_auth(client_google_mode: httpx.AsyncClient) -> None:
    assert (await client_google_mode.get("/api/v1/research/usage")).status_code == 401
    r = await client_google_mode.get("/api/v1/research/sources", params={"session_id": "s1"})
    assert r.status_code == 401


async def test_lifespan_opens_research_on_injected_providers(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    research: ResearchRuntime = app.state.research
    assert research.providers is app.state.research_providers
    assert research.session_factory is app.state.session_factory
