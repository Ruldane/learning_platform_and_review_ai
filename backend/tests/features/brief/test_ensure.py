"""Création du brief du jour local (P12, D162) : un brief et une session par jour, quel que soit le
nombre d'ouvertures simultanées ; le jour est celui de January ; sans moteur, les rubriques du code
sont là et le conseil se dit indisponible."""

import asyncio
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.daily import Brief
from app.features.brief.repository import BriefRepository
from app.features.brief.service import ensure
from app.features.brief.service.ensure import ensure_today
from app.features.brief.service.runtime import BriefRuntime
from app.features.brief.service.sections import build_sections
from tests.features.brief.conftest import NOW, OTHER, TODAY, Env
from tests.features.brief.support import (
    add_cards,
    add_user,
    brief_sessions,
    briefs,
    get_today,
)
from tests.sessions_support import act_as


async def test_concurrent_ensure_creates_one_brief(env: Env, rt: BriefRuntime) -> None:
    results = await asyncio.gather(
        *(ensure_today(rt, env.user_id, origin="opening") for _ in range(5))
    )
    assert sorted(created for _, created in results) == [False] * 4 + [True]
    assert len({brief.id for brief, _ in results}) == 1
    [row] = await briefs(env)
    assert row.day == TODAY and row.origin == "opening" and row.advice_status == "pending"
    assert await brief_sessions(env) == 1  # une seule session
    assert env.launcher.started == [("daily_brief", {"brief_id": row.id})]
    assert row.session_id is not None


async def test_second_get_same_brief_no_new_session(client: httpx.AsyncClient, env: Env) -> None:
    first = await get_today(client)
    second = await get_today(client)
    assert first["id"] == second["id"] and first["session_id"] == second["session_id"]
    assert first["session_id"] is not None and len(env.launcher.started) == 1
    assert len(await briefs(env)) == 1


async def test_double_read_of_strict_mode_creates_one_brief(
    client: httpx.AsyncClient, env: Env
) -> None:
    replies = await asyncio.gather(
        client.get("/api/v1/brief/today"), client.get("/api/v1/brief/today")
    )
    assert [r.status_code for r in replies] == [200, 200]
    assert replies[0].json()["id"] == replies[1].json()["id"]
    assert len(env.launcher.started) == 1


async def test_yesterday_brief_replaced_by_today_at_opening(
    client: httpx.AsyncClient, env: Env
) -> None:
    env.at(NOW - timedelta(days=1))
    yesterday = await get_today(client)
    env.at(NOW)
    today = await get_today(client)
    assert yesterday["day"] == "2026-11-16" and today["day"] == "2026-11-17"
    assert yesterday["id"] != today["id"] and today["origin"] == "opening"
    assert [row.day for row in await briefs(env)] == [TODAY - timedelta(days=1), TODAY]
    assert len(env.launcher.started) == 2


async def test_brief_day_is_the_local_day_not_the_utc_day(
    client: httpx.AsyncClient, env: Env
) -> None:
    env.at(datetime(2026, 11, 16, 23, 30, tzinfo=UTC))  # 00 h 30 à Paris : déjà le 17
    assert (await get_today(client))["day"] == "2026-11-17"
    env.at(datetime(2026, 11, 17, 22, 59, tzinfo=UTC))  # 23 h 59 à Paris : encore le 17
    assert (await get_today(client))["day"] == "2026-11-17"
    assert len(await briefs(env)) == 1


async def test_the_inserter_alone_launches_the_session(
    env: Env, rt: BriefRuntime, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Un autre processus insère le brief du jour entre le calcul des rubriques et l'insertion :
    ce processus-ci perd la course, rend le brief de l'autre et ne lance rien."""
    real = build_sections

    async def rival(
        rt_: BriefRuntime, db: AsyncSession, user_id: str, today: date
    ) -> dict[str, Any]:
        sections = await real(rt_, db, user_id, today)
        async with rt_.session_factory() as other:
            other.add(Brief(user_id=user_id, day=today, origin="schedule", sections=sections))
            await other.commit()
        return sections

    monkeypatch.setattr(ensure, "build_sections", rival)
    brief, created = await ensure_today(rt, env.user_id, origin="opening")
    assert created is False and brief.origin == "schedule"
    assert env.launcher.started == [] and brief.session_id is None
    assert len(await briefs(env)) == 1


async def test_insert_conflict_changes_nothing(env: Env, rt: BriefRuntime) -> None:
    async with rt.session_factory() as db:
        repo = BriefRepository(db, env.user_id)
        first = await repo.insert_if_absent(
            day=TODAY, origin="opening", sections={"a": 1}, offer_keys=[], now=NOW
        )
        again = await repo.insert_if_absent(
            day=TODAY, origin="schedule", sections={"a": 2}, offer_keys=[], now=NOW
        )
        await db.commit()
    assert first is not None and again is None
    [row] = await briefs(env)
    assert (row.origin, row.sections) == ("opening", {"a": 1})


async def test_brief_without_llm_has_code_rubrics(client: httpx.AsyncClient, env: Env) -> None:
    await add_cards(env, 3)
    env.launcher.refuse = True  # moteur absent : la session ne peut pas être lancée
    body = await get_today(client)
    assert body["advice_status"] == "unavailable" and body["advice"] is None
    assert body["session_id"] is None and body["resource"] is None
    assert body["reviews"] == {"queue": 3, "remaining": 0}  # les rubriques du code sont intactes
    again = await get_today(client)
    assert again["id"] == body["id"] and again["advice_status"] == "unavailable"
    env.launcher.refuse = False
    assert (await get_today(client))["advice_status"] == "unavailable"  # jamais relancé
    assert env.launcher.started == []


async def test_other_user_brief_isolated(client: httpx.AsyncClient, env: Env) -> None:
    await add_user(env, OTHER)
    await add_cards(env, 4)
    await add_cards(env, 9, user=OTHER)
    mine = await get_today(client)
    act_as(env.app, OTHER)
    theirs = await get_today(client)
    assert mine["id"] != theirs["id"]
    assert (mine["reviews"]["queue"], theirs["reviews"]["queue"]) == (4, 9)
    assert [row.id for row in await briefs(env)] == [mine["id"]]
    assert [row.id for row in await briefs(env, OTHER)] == [theirs["id"]]
    assert len(env.launcher.started) == 2


async def test_launch_failure_of_any_kind_makes_the_advice_unavailable(
    client: httpx.AsyncClient, env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def broken(*args: object, **kwargs: object) -> str:
        raise RuntimeError("panne du lanceur : donnée secrète")

    monkeypatch.setattr(env.launcher, "start", broken)
    body = await get_today(client)
    assert body["advice_status"] == "unavailable" and body["block"] is None
