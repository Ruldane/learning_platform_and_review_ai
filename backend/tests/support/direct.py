"""Matériel des tests d'écriture directe (10.W) : un programme brouillon écrit par le vrai port du
programme dans l'application réelle, la garantie « aucun agent » (aucune session, aucun appel au
modèle) et un client du MCP sur le registre réel."""

from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.agents import AgentSession, LlmCall
from app.features.memory.service.direct import drain_indexing
from app.features.program.service.programs import load
from app.features.program.service.store import AgentProgramStore
from tests.features.program.support import MONDAY, add_goal, sample_plan
from tests.mcp.support import Mcp

API = "/api/v1"
OTHER = "autre-utilisatrice"
Factory = async_sessionmaker[AsyncSession]


@dataclass(frozen=True)
class Seed:
    user_id: str
    program_id: str
    weeks: list[str]  # identifiants, par rang
    modules: list[str]  # identifiants, par semaine puis rang


async def seed_program(app: FastAPI) -> Seed:
    """Un brouillon de deux semaines et deux modules, rangé par le vrai port du Stratège (sans
    session d'agent réelle)."""
    user_id: str = app.state.local_user_id
    rows = await add_goal(app.state.session_factory, user_id)
    saved = await AgentProgramStore(app.state.program).save_draft(
        user_id,
        "s-draft",
        rows.goal_id,
        sample_plan(),
        revision=0,
        start_date=MONDAY,
        reason="Première version du Stratège",
    )
    async with app.state.session_factory() as db:
        loaded = await load(db, user_id, saved.program_id)
    return Seed(
        user_id,
        saved.program_id,
        [w.id for w in loaded.weeks],
        [m.id for m in loaded.modules],
    )


@pytest.fixture
async def drafted(client: httpx.AsyncClient, app: FastAPI) -> Seed:
    return await seed_program(app)


async def agent_traces(app: FastAPI) -> tuple[int, int]:
    """`(sessions d'agents, appels au modèle)` en base."""
    async with app.state.session_factory() as db:
        sessions = int(
            (await db.execute(select(func.count()).select_from(AgentSession))).scalar_one()
        )
        calls = int((await db.execute(select(func.count()).select_from(LlmCall))).scalar_one())
    return sessions, calls


async def assert_no_agent(app: FastAPI) -> None:
    """Aucun graphe n'a été lancé (aucune session d'agent) et aucun modèle n'a été appelé."""
    assert await agent_traces(app) == (0, 0)


@pytest.fixture
async def claude(client: httpx.AsyncClient, app: FastAPI) -> AsyncIterator[Mcp]:
    """Le client du MCP sur l'application réelle (registre des déclarations réelles)."""
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as http:
        yield Mcp(http)


def lesson_text(sentence: str) -> str:
    """Une leçon d'au moins 300 caractères (le plancher de l'écriture directe) de `sentence`."""
    return "# Une leçon\n\n" + " ".join([sentence] * (300 // len(sentence) + 2)) + "\n"


@pytest.fixture
async def settled_indexing(client: httpx.AsyncClient) -> AsyncIterator[None]:
    """Attend, avant l'arrêt de l'application, l'indexation de fond lancée par les écritures."""
    yield
    await drain_indexing()
