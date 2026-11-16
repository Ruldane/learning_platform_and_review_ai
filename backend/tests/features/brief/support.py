"""Gestes communs des tests du brief : lire les lignes, semer des relevés du radar, des briefs, des
fiches et des utilisateurs. Données fictives (« Société Fictive », `example.org`)."""

from collections.abc import Sequence
from datetime import date, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import func, select

from app.db.models.accounts import User
from app.db.models.agents import AgentSession
from app.db.models.daily import Brief, JobRun, RadarRun
from app.db.models.study import Flashcard
from app.features.brief.service.sections import build_sections
from tests.features.brief.conftest import NOW, TODAY, Env

API = "/api/v1/brief/today"


async def get_today(client: httpx.AsyncClient) -> dict[str, Any]:
    r = await client.get(API)
    assert r.status_code == 200, r.text
    body: dict[str, Any] = r.json()
    return body


async def briefs(env: Env, user: str | None = None) -> list[Brief]:
    async with env.rt.session_factory() as db:
        stmt = select(Brief).where(Brief.user_id == (user or env.user_id)).order_by(Brief.day)
        return list((await db.execute(stmt)).scalars())


async def jobs(env: Env, user: str | None = None) -> list[JobRun]:
    async with env.rt.session_factory() as db:
        stmt = select(JobRun).where(
            JobRun.user_id == (user or env.user_id), JobRun.name == "daily_brief"
        )
        return list((await db.execute(stmt.order_by(JobRun.created_at))).scalars())


async def brief_sessions(env: Env) -> int:
    async with env.rt.session_factory() as db:
        stmt = (
            select(func.count())
            .select_from(AgentSession)
            .where(AgentSession.graph == "daily_brief")
        )
        return int((await db.execute(stmt)).scalar_one())


async def sections_for(env: Env, user: str | None = None, today: date = TODAY) -> dict[str, Any]:
    async with env.rt.session_factory() as db:
        return await build_sections(env.rt, db, user or env.user_id, today)


async def add_user(env: Env, user_id: str) -> None:
    async with env.rt.session_factory() as db:
        db.add(User(id=user_id, user_id=user_id))
        await db.commit()


def posting(number: int, score: int | None, **over: Any) -> dict[str, Any]:
    """Une offre examinée d'un relevé (analysée, notée), au lien `example.org/offres/<n>`."""
    url = f"https://jobs.example.org/offres/{number}"
    entry: dict[str, Any] = {
        "ref": f"p{number}",
        "url": url,
        "key": url,
        "domain": "jobs.example.org",
        "read": "ok",
        "title": f"Poste {number}",
        "company": "Société Fictive",
        "level": "confirme",
        "skills": [],
        "tools": [],
    }
    if score is not None:
        entry["score"] = score
    return entry | over


async def add_run(
    env: Env,
    postings: Sequence[dict[str, Any]],
    *,
    finished_at: datetime | None = None,
    user: str | None = None,
    status: str = "done",
) -> str:
    """Un relevé du radar fini à `finished_at` (deux heures avant `NOW` par défaut)."""
    async with env.rt.session_factory() as db:
        row = RadarRun(
            user_id=user or env.user_id,
            role="Ingénieur IA",
            zone="Lyon",
            role_norm="ingenieur ia",
            zone_norm="lyon",
            trigger="manual",
            status=status,
            postings=list(postings),
            finished_at=finished_at or NOW - timedelta(hours=2),
        )
        db.add(row)
        await db.commit()
        return row.id


async def add_cards(env: Env, count: int, *, due: date = TODAY, user: str | None = None) -> None:
    async with env.rt.session_factory() as db:
        db.add_all(
            Flashcard(
                user_id=user or env.user_id,
                front=f"Recto {i}-{due}",
                back="Verso",
                front_hash=f"{i}-{due}",
                source="lesson",
                step=2,
                due_date=due,
            )
            for i in range(count)
        )
        await db.commit()


async def applied(client: httpx.AsyncClient, days: int, **fields: Any) -> str:
    """Une fiche « Postulée » il y a `days` jours (jour de `NOW`)."""
    body = {
        "company": "Société Fictive",
        "title": "Développeuse IA",
        "status": "applied",
        "applied_on": str(TODAY - timedelta(days=days)),
    } | fields
    r = await client.post("/api/v1/applications", json=body)
    assert r.status_code == 201, r.text
    return str(r.json()["application"]["id"])
