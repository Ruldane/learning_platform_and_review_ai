"""Gestes communs des tests de l'étude guidée : démarrer, lire, terminer, compter des lignes."""

from typing import Any

import httpx
from sqlalchemy import func, select

from app.db.models.study import StudySession
from tests.features.study.conftest import Seeded

API = "/api/v1/study-sessions"


async def start(client: httpx.AsyncClient, **body: Any) -> httpx.Response:
    return await client.post(API, json=body)


async def started(client: httpx.AsyncClient, **body: Any) -> dict[str, Any]:
    r = await start(client, **body)
    assert r.status_code == 202, r.text
    out: dict[str, Any] = r.json()
    return out


async def study(client: httpx.AsyncClient, study_id: str) -> dict[str, Any]:
    r = await client.get(f"{API}/{study_id}")
    assert r.status_code == 200, r.text
    out: dict[str, Any] = r.json()
    return out


async def patch(client: httpx.AsyncClient, study_id: str, **body: Any) -> httpx.Response:
    return await client.patch(f"{API}/{study_id}", json=body)


async def count(s: Seeded, model: type, **where: Any) -> int:
    async with s.rt.session_factory() as db:
        stmt = select(func.count()).select_from(model)
        for key, value in where.items():
            stmt = stmt.where(getattr(model, key) == value)
        return int((await db.execute(stmt)).scalar_one())


async def row(s: Seeded, study_id: str) -> StudySession:
    async with s.rt.session_factory() as db:
        found = await db.get(StudySession, study_id)
        assert found is not None
        return found
