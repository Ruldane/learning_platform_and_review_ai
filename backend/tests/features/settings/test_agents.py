"""`GET /settings/agents` : le catalogue des agents dont le modèle se surcharge (P17)."""

import httpx
from fastapi import FastAPI

from app.agents.registry import AGENTS
from app.features.settings.agents import agent_catalogue
from tests.sessions_support import act_as

API = "/api/v1/settings/agents"


async def test_agents_catalogue_excludes_demo(client: httpx.AsyncClient) -> None:
    r = await client.get(API)
    assert r.status_code == 200
    names = [agent["name"] for agent in r.json()]
    assert names and not [name for name in names if name.startswith("demo_")]
    assert {"strategist", "writer", "tutor", "designer"} <= set(names)


async def test_agents_catalogue_follows_the_registry_order_with_tiers(
    client: httpx.AsyncClient,
) -> None:
    expected = [
        {"name": spec.name, "tier": spec.tier}
        for spec in AGENTS.values()
        if not spec.name.startswith("demo_")
    ]
    assert (await client.get(API)).json() == expected
    assert [agent.model_dump() for agent in agent_catalogue()] == expected


async def test_agents_catalogue_is_the_same_for_every_account(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    mine = (await client.get(API)).json()
    act_as(app, "autre-compte")
    assert (await client.get(API)).json() == mine


async def test_agents_catalogue_needs_a_user(client_google_mode: httpx.AsyncClient) -> None:
    assert (await client_google_mode.get(API)).status_code == 401
