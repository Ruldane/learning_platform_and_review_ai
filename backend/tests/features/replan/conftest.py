"""Matériel des tests de la feature `replan` (D106) : la vraie base de test, le vrai port du
programme (validation sans production des leçons), le vrai port de la replanification, un
lanceur factice (aucune session réelle, aucun LLM) et une horloge figée (mercredi 18/11, Paris).
Programme `sample_plan` : semaine 1 du 16/11 (665 min), semaine 2 du 23/11 (205 min)."""

from collections.abc import AsyncIterator
from datetime import UTC, date, datetime
from typing import Any

import pytest
from sqlalchemy import select

from app.agents.tools.plan_schema import PlanDraft
from app.core.providers import MemoryProviders
from app.db.models.program import PlanVersion, Task
from app.features.memory.service.runtime import memory_runtime
from app.features.program.service.programs import load
from app.features.program.service.runtime import ProgramRuntime
from app.features.program.service.store import AgentProgramStore
from app.features.replan.service.runtime import ReplanRuntime
from app.features.replan.service.store import AgentReplanStore
from tests.features.lessons.conftest import RecordingLauncher
from tests.features.program.support import MONDAY, Factory, add_goal, sample_plan

ME, OTHER = "moi", "autre"
NOW = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)  # mercredi de la semaine 1, 10 h à Paris
TODAY = date(2026, 11, 18)
CAP = 714


@pytest.fixture
async def program_rt(
    db_session_factory: Factory, memory_providers: MemoryProviders
) -> AsyncIterator[ProgramRuntime]:
    async with memory_runtime(db_session_factory, memory_providers) as memory:
        yield ProgramRuntime(db_session_factory, memory)


@pytest.fixture
def launcher(db_session_factory: Factory) -> RecordingLauncher:
    return RecordingLauncher(db_session_factory)


@pytest.fixture
def replan_rt(
    db_session_factory: Factory, program_rt: ProgramRuntime, launcher: RecordingLauncher
) -> ReplanRuntime:
    return ReplanRuntime(db_session_factory, launcher, program_rt, now=lambda: NOW)


@pytest.fixture
def store(replan_rt: ReplanRuntime) -> AgentReplanStore:
    return AgentReplanStore(replan_rt)


async def drafted(
    program_rt: ProgramRuntime,
    user_id: str = ME,
    plan: PlanDraft | None = None,
    start: date = MONDAY,
) -> str:
    """Un brouillon écrit par le vrai port du Stratège (session « s-draft »)."""
    rows = await add_goal(program_rt.session_factory, user_id)
    saved = await AgentProgramStore(program_rt).save_draft(
        user_id, "s-draft", rows.goal_id, plan or sample_plan(), revision=0,
        start_date=start, reason="Première version du Stratège",
    )  # fmt: skip
    return saved.program_id


async def validated(
    program_rt: ProgramRuntime,
    user_id: str = ME,
    plan: PlanDraft | None = None,
    start: date = MONDAY,
) -> str:
    """Un programme validé (sans production des leçons : `ProgramRuntime.lessons` vide)."""
    program_id = await drafted(program_rt, user_id, plan, start)
    await AgentProgramStore(program_rt).validate(user_id, "s-draft", program_id)
    return program_id


async def tasks_of(factory: Factory, program_id: str, user_id: str = ME) -> list[Task]:
    async with factory() as db:
        return (await load(db, user_id, program_id)).tasks


async def week_loads(factory: Factory, program_id: str, user_id: str = ME) -> list[int]:
    """Charge de chaque semaine du programme (tâches comptées par leur jour, D88 §1)."""
    async with factory() as db:
        loaded = await load(db, user_id, program_id)
        return [loaded.week_load(week) for week in loaded.weeks]


async def versions(factory: Factory, program_id: str) -> list[dict[str, Any]]:
    async with factory() as db:
        rows = (
            await db.execute(
                select(PlanVersion)
                .where(PlanVersion.program_id == program_id)
                .order_by(PlanVersion.version)
            )
        ).scalars()
        return [{"version": v.version, "kind": v.kind, "status": v.status} for v in rows]
