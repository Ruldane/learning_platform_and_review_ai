"""`GET /costs` : la fenêtre (7, 30 ou 90 jours), l'isolation, aucun écho, aucun journal."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agents import LlmCall
from tests.sessions_support import act_as

API = "/api/v1/costs"
SECRET = "agent-ultra-secret"


async def seed(db: AsyncSession, user_id: str, days_ago: int = 2, **over: Any) -> None:
    fields: dict[str, Any] = {
        "user_id": user_id,
        "created_at": datetime.now(UTC) - timedelta(days=days_ago),
        "graph": "capture",
        "agent": "extractor",
        "provider": "glm",
        "model": "glm-5.3-flash",
        "tokens_in": 100,
        "tokens_out": 50,
        "cost_usd": 0.25,
    }
    db.add(LlmCall(**{**fields, **over}))
    await db.commit()


async def test_costs_route_default_30_days(
    client: httpx.AsyncClient, app: FastAPI, db_session: AsyncSession
) -> None:
    await seed(db_session, app.state.local_user_id)
    await seed(db_session, app.state.local_user_id, days_ago=45)  # hors des 30 jours
    r = await client.get(API)
    assert r.status_code == 200
    body = r.json()
    assert body["days"] == 30 and len(body["by_day"]) == 30
    assert body["total"] == {
        "calls": 1,
        "tokens_in": 100,
        "tokens_out": 50,
        "cost_usd": 0.25,
        "estimated_calls": 0,
    }
    assert [row["key"] for row in body["by_model"]] == ["glm:glm-5.3-flash"]
    assert [row["key"] for row in body["by_feature"]] == ["capture"]
    assert [row["key"] for row in body["by_agent"]] == ["extractor"]


@pytest.mark.parametrize("days", [7, 30, 90])
async def test_costs_days_in_windows_is_accepted(client: httpx.AsyncClient, days: int) -> None:
    r = await client.get(API, params={"days": str(days)})
    assert r.status_code == 200, r.text
    assert r.json()["days"] == days and len(r.json()["by_day"]) == days


async def test_costs_window_changes_what_is_counted(
    client: httpx.AsyncClient, app: FastAPI, db_session: AsyncSession
) -> None:
    await seed(db_session, app.state.local_user_id, days_ago=20)
    assert (await client.get(API, params={"days": "7"})).json()["total"]["calls"] == 0
    assert (await client.get(API, params={"days": "30"})).json()["total"]["calls"] == 1
    assert (await client.get(API, params={"days": "90"})).json()["total"]["calls"] == 1


@pytest.mark.parametrize("days", ["0", "8", "abc", "-30", "", "7.0", " 7", "²", "٧", "1e1", "700"])
async def test_costs_days_not_in_windows_is_422(client: httpx.AsyncClient, days: str) -> None:
    r = await client.get(API, params={"days": days})
    assert r.status_code == 422
    assert r.json()["error"]["details"] == {"fields": ["days"]}
    assert f"={days}" not in r.text and (not days or days not in r.json()["error"]["message"])


async def test_costs_needs_a_user(client_google_mode: httpx.AsyncClient) -> None:
    assert (await client_google_mode.get(API)).status_code == 401


async def test_other_user_calls_invisible(
    client: httpx.AsyncClient, app: FastAPI, db_session: AsyncSession
) -> None:
    await seed(db_session, app.state.local_user_id)
    await seed(db_session, "autre-utilisatrice", cost_usd=9.0, agent=SECRET)
    mine = (await client.get(API)).json()
    assert mine["total"]["calls"] == 1 and mine["total"]["cost_usd"] == 0.25
    assert SECRET not in str(mine)
    act_as(app, "autre-utilisatrice")
    theirs = (await client.get(API)).json()
    assert theirs["total"]["calls"] == 1 and theirs["total"]["cost_usd"] == 9.0
    act_as(app, "troisieme-utilisatrice")
    nobody = (await client.get(API)).json()
    assert nobody["total"]["calls"] == 0 and nobody["by_model"] == []
    assert len(nobody["by_day"]) == 30


async def test_costs_never_logged(
    caplog: pytest.LogCaptureFixture,
    client: httpx.AsyncClient,
    app: FastAPI,
    db_session: AsyncSession,
) -> None:
    caplog.set_level(logging.DEBUG, logger="app")
    await seed(db_session, app.state.local_user_id, agent=SECRET, graph="graphe-ultra-secret")
    await seed(db_session, app.state.local_user_id, model="modele-ultra-secret")
    assert (await client.get(API)).status_code == 200
    assert (await client.get(API, params={"days": "secret-ultra-valeur"})).status_code == 422
    logged = "\n".join(record.getMessage() for record in caplog.records)
    for secret in (SECRET, "graphe-ultra-secret", "modele-ultra-secret", "secret-ultra-valeur"):
        assert secret not in logged


def test_costs_contract_keeps_the_enum_and_documents_the_422(app: FastAPI) -> None:
    operation = app.openapi()["paths"]["/api/v1/costs"]["get"]
    [days] = [p for p in operation["parameters"] if p["name"] == "days"]
    assert days["schema"]["enum"] == [7, 30, 90] and days["schema"]["default"] == 30
    assert days["schema"]["type"] == "integer"
    assert "days" in operation["responses"]["422"]["description"]


def test_drafts_route_documents_its_503(app: FastAPI) -> None:
    operation = app.openapi()["paths"]["/api/v1/projects/{project_id}/drafts"]["post"]
    assert "drafts_unavailable" in operation["responses"]["503"]["description"]
