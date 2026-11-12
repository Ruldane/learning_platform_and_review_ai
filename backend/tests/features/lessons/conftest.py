"""Matériel des tests de la production des leçons (D91) : la vraie base de test, le vrai port
(`AgentLessonStore`), un lanceur qui écrit la session `running` sans faire tourner de graphe, et
un programme validé par le vrai port du programme. Aucun réseau ni LLM."""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import func, select

from app.agents.runtime.repositories import SessionRepository
from app.agents.tools.plan_schema import PlanDraft
from app.core.errors import AppError
from app.core.providers import MemoryProviders, PublishingProviders
from app.core.security import Cipher
from app.db.models.agents import AgentSession
from app.features.lessons.service.runtime import LessonsRuntime
from app.features.lessons.service.store import AgentLessonStore
from app.features.memory.service.runtime import memory_runtime
from app.features.program.service.programs import load
from app.features.program.service.runtime import ProgramRuntime
from app.features.program.service.store import AgentProgramStore
from app.features.research.service.runtime import ResearchRuntime
from app.features.settings.keys_service import DbKeyReader
from app.scheduler.base import JobContext
from tests.features.program.support import MONDAY, Factory, add_goal, sample_plan
from tests.support.memory import FakeWebReader
from tests.support.research import FakeFetcher, fake_research_providers

ME, OTHER = "moi", "autre"
DRAFT_SESSION = "s-draft"


@dataclass
class RecordingLauncher:
    """Lanceur factice : crée la session `running` en base (comme le runner) et note
    `(parcours, entrée)` ; `refuse` : lève comme un moteur indisponible."""

    factory: Factory
    started: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    refuse: bool = False

    async def start(
        self,
        user_id: str,
        graph: str,
        input: dict[str, Any],
        *,
        subject_type: str | None = None,
        subject_id: str | None = None,
    ) -> str:
        if self.refuse:
            raise AppError("engine_unavailable", "Le moteur d'agents n'est pas prêt.", 503)
        async with self.factory() as db:
            row = await SessionRepository(db, user_id).add(
                graph=graph,
                status="running",
                input=input,
                subject_type=subject_type,
                subject_id=subject_id,
            )
            await db.commit()
        self.started.append((graph, dict(input)))
        return row.id

    async def end(self, user_id: str, session_id: str, status: str = "completed") -> None:
        async with self.factory() as db:
            await SessionRepository(db, user_id).update(session_id, status=status)
            await db.commit()


async def count_open_sessions(factory: Factory, graph: str) -> int:
    async with factory() as db:
        stmt = (
            select(func.count())
            .select_from(AgentSession)
            .where(
                AgentSession.graph == graph,
                AgentSession.status.in_(["running", "waiting_user", "paused"]),
            )
        )
        return int((await db.execute(stmt)).scalar_one())


@pytest.fixture
def launcher(db_session_factory: Factory) -> RecordingLauncher:
    return RecordingLauncher(db_session_factory)


@pytest.fixture
def fetcher() -> FakeFetcher:
    return FakeFetcher()


@pytest.fixture
async def lessons_rt(
    db_session_factory: Factory,
    memory_providers: MemoryProviders,
    publishing_providers: PublishingProviders,
    launcher: RecordingLauncher,
    fake_web: FakeWebReader,
    fetcher: FakeFetcher,
) -> AsyncIterator[LessonsRuntime]:
    keys = DbKeyReader(db_session_factory, Cipher(Fernet.generate_key()), {})
    research = ResearchRuntime(
        db_session_factory, fake_research_providers(fake_web, fetcher=fetcher), keys
    )
    async with memory_runtime(db_session_factory, memory_providers) as memory:
        yield LessonsRuntime(
            db_session_factory,
            launcher,
            memory,
            research,
            memory_providers.storage,
            publishing_providers,
        )


@pytest.fixture
def fake_web() -> FakeWebReader:
    return FakeWebReader()


@pytest.fixture
def program_rt(lessons_rt: LessonsRuntime) -> ProgramRuntime:
    return ProgramRuntime(lessons_rt.session_factory, lessons_rt.memory, lessons=lessons_rt)


@pytest.fixture
def store(lessons_rt: LessonsRuntime) -> AgentLessonStore:
    return AgentLessonStore(lessons_rt)


@pytest.fixture
def job_ctx(lessons_rt: LessonsRuntime) -> JobContext:
    return JobContext(lessons_rt.session_factory, lessons_rt.launcher, lessons_rt)  # type: ignore[arg-type]


@dataclass(frozen=True)
class Program:
    program_id: str
    goal_id: str
    modules: list[str]  # par semaine puis rang


async def draft_program(
    program_rt: ProgramRuntime, user_id: str = ME, draft: PlanDraft | None = None
) -> Program:
    """Un brouillon écrit par le vrai port du programme (session « s-draft »), début `MONDAY`."""
    factory = program_rt.session_factory
    rows = await add_goal(factory, user_id)
    saved = await AgentProgramStore(program_rt).save_draft(
        user_id,
        DRAFT_SESSION,
        rows.goal_id,
        draft or sample_plan(),
        revision=0,
        start_date=MONDAY,
        reason="Première version du Stratège",
    )

    async with factory() as db:
        loaded = await load(db, user_id, saved.program_id)
    return Program(saved.program_id, rows.goal_id, [m.id for m in loaded.modules if not m.skipped])


async def validate(program_rt: ProgramRuntime, program: Program, user_id: str = ME) -> None:
    """Validation par le port du Stratège (`finalize`) : elle lance la production."""
    await AgentProgramStore(program_rt).validate(user_id, DRAFT_SESSION, program.program_id)
