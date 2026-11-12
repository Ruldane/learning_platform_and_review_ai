from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx
import pytest
from fastapi import FastAPI

from app.core.providers import MemoryProviders
from app.features.memory.service.runtime import memory_runtime
from app.features.program.service.budget import Budget
from app.features.program.service.runtime import ProgramRuntime
from app.features.program.service.store import AgentProgramStore
from tests.features.program.support import MONDAY, Factory, add_goal, sample_plan


@pytest.fixture
def budget() -> Budget:
    return Budget(weekday_minutes=120, weekend_minutes=240)  # 840 par semaine, plafond 714


# --- Port réel sur une base de test (sans l'app) -------------------------------------------------


@pytest.fixture
async def program_rt(
    db_session_factory: Factory, memory_providers: MemoryProviders
) -> AsyncIterator[ProgramRuntime]:
    async with memory_runtime(db_session_factory, memory_providers) as memory:
        yield ProgramRuntime(db_session_factory, memory)


@pytest.fixture
def store(program_rt: ProgramRuntime) -> AgentProgramStore:
    return AgentProgramStore(program_rt)


# --- Programme en brouillon dans l'app (routes) ---------------------------------------------------


@dataclass(frozen=True)
class Draft:
    program_id: str
    goal_id: str
    user_id: str


@pytest.fixture
async def draft_program(client: httpx.AsyncClient, app: FastAPI) -> Draft:
    """Un brouillon écrit par le vrai port (session « s-draft », sans session d'agent réelle :
    la validation se fait en ligne)."""
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
    return Draft(saved.program_id, rows.goal_id, user_id)
