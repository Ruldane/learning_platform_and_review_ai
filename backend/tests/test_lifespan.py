import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path

import httpx
import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

import app.main as main_module
from app.agents.runtime.bus import EventBus
from app.agents.runtime.launcher import SessionLauncher
from app.agents.runtime.runner import SessionRunner
from app.bootstrap import agent_ports, study_runtimes
from app.config import Settings
from app.core.providers import MemoryProviders, ResearchProviders
from app.core.security import Cipher, KnownSecrets
from app.db.models.accounts import User
from app.features.auth.service import AuthService
from app.features.learning.service.runtime import LearningRuntime
from app.features.learning.service.store import AgentCouncilStore
from app.features.lessons.service.runtime import LessonsRuntime
from app.features.lessons.service.store import AgentLessonStore
from app.features.memory.service.gateway import AgentMemoryGateway
from app.features.program.service.runtime import ProgramRuntime
from app.features.program.service.store import AgentProgramStore
from app.features.quiz.service.store import AgentQuizStore
from app.features.research.service.gateway import AgentWebGateway
from app.features.study.service.store import AgentStudyStore
from app.main import create_app
from app.scheduler.base import JobContext, JobSpec
from tests.support.memory import fake_memory_providers


async def test_lifespan_creates_secret_and_cipher(settings: Settings, db_engine: object) -> None:
    app = create_app(settings)
    async with LifespanManager(app):
        assert settings.secret_path.exists()
        cipher = app.state.cipher
        assert isinstance(cipher, Cipher)
        assert cipher.decrypt(cipher.encrypt("sk-ant-demo-123456")) == "sk-ant-demo-123456"


async def test_lifespan_registers_env_keys_as_known_secrets(
    settings: Settings, db_engine: object
) -> None:
    configured = settings.model_copy(update={"brave_api_key": "brave-cle-de-test-0001"})
    async with LifespanManager(create_app(configured)):
        assert "brave-cle-de-test-0001" in KnownSecrets.values()


async def test_lifespan_restart_keeps_local_user_and_secret(
    settings: Settings, db_session: AsyncSession
) -> None:
    first_app = create_app(settings)
    async with LifespanManager(first_app):
        first_id = first_app.state.local_user_id
        first_token = first_app.state.cipher.encrypt("valeur")
    second_app = create_app(settings)
    async with LifespanManager(second_app):
        assert second_app.state.local_user_id == first_id
        assert second_app.state.cipher.decrypt(first_token) == "valeur"
    count = await db_session.scalar(select(func.count()).select_from(User))
    assert count == 1


async def test_missing_table_gives_alembic_hint(settings: Settings) -> None:
    # Aucune fixture de schéma : la table `users` n'existe pas.
    with pytest.raises(RuntimeError, match="alembic upgrade head"):
        async with LifespanManager(create_app(settings)):
            pass


async def test_other_operational_error_is_not_relabeled(
    settings: Settings, db_engine: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    error = OperationalError("SELECT 1", {}, Exception("database is locked"))

    async def locked(self: AuthService) -> None:
        raise error

    monkeypatch.setattr(AuthService, "ensure_local_user", locked)
    with pytest.raises(OperationalError) as caught:
        async with LifespanManager(create_app(settings)):
            pass
    assert caught.value is error


async def test_http_client_is_closed_when_composition_fails(
    settings: Settings, db_engine: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    created: list[httpx.AsyncClient] = []
    original = httpx.AsyncClient

    def tracking(*args: object, **kwargs: object) -> httpx.AsyncClient:
        client = original(*args, **kwargs)  # type: ignore[arg-type]
        created.append(client)
        return client

    def boom(*args: object, **kwargs: object) -> None:
        raise ValueError("composition cassée")

    monkeypatch.setattr("app.main.httpx.AsyncClient", tracking)
    monkeypatch.setattr("app.main.build_providers", boom)
    with pytest.raises(ValueError, match="composition cassée"):
        async with LifespanManager(create_app(settings)):
            pass
    # Sondes de santé et test de la clé Brave (D74) : tous deux fermés.
    assert len(created) == 2 and all(c.is_closed for c in created)


async def test_shutdown_stops_runner_then_bus_then_engine(
    settings: Settings, db_engine: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    order: list[str] = []
    original_dispose = AsyncEngine.dispose
    original_shutdown = SessionRunner.shutdown

    async def runner_shutdown(self: SessionRunner) -> None:
        order.append("runner")
        await original_shutdown(self)

    async def bus_aclose(self: EventBus) -> None:
        order.append("bus")

    async def dispose(self: AsyncEngine, close: bool = True) -> None:
        order.append("engine")
        await original_dispose(self, close)

    monkeypatch.setattr(SessionRunner, "shutdown", runner_shutdown)
    monkeypatch.setattr(EventBus, "aclose", bus_aclose)
    monkeypatch.setattr(AsyncEngine, "dispose", dispose)
    app = create_app(settings)
    async with LifespanManager(app):
        assert isinstance(app.state.runtime.bus, EventBus)
    assert order == ["runner", "bus", "engine"]


async def test_lifespan_uses_injected_memory_providers(
    app: FastAPI, memory_providers: MemoryProviders, client: httpx.AsyncClient
) -> None:
    assert app.state.memory_providers is memory_providers


async def test_lifespan_builds_memory_providers_when_none_injected(
    settings: Settings, db_engine: object, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    built = fake_memory_providers(tmp_path)
    seen: list[Settings] = []
    closed: list[bool] = []

    @asynccontextmanager
    async def fake_composition(given: Settings) -> AsyncIterator[MemoryProviders]:
        seen.append(given)
        try:
            yield built
        finally:
            closed.append(True)

    monkeypatch.setattr("app.main.open_memory_providers", fake_composition)
    app = create_app(settings)
    async with LifespanManager(app):
        assert app.state.memory_providers is built and closed == []
    assert seen == [settings] and closed == [True]


async def test_injected_memory_providers_skip_the_composition(
    settings: Settings,
    db_engine: object,
    memory_providers: MemoryProviders,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(given: Settings) -> None:
        raise AssertionError("la composition ne doit pas être appelée")

    monkeypatch.setattr("app.main.open_memory_providers", boom)
    async with LifespanManager(create_app(settings, memory_providers=memory_providers)):
        pass


async def test_lifespan_uses_injected_research_providers(
    app: FastAPI, research_providers: ResearchProviders, client: httpx.AsyncClient
) -> None:
    assert app.state.research_providers is research_providers


async def test_lifespan_builds_research_providers_on_the_memory_web_reader(
    settings: Settings,
    db_engine: object,
    memory_providers: MemoryProviders,
    research_providers: ResearchProviders,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[tuple[Settings, object]] = []
    closed: list[bool] = []

    @asynccontextmanager
    async def fake_composition(given: Settings, web: object) -> AsyncIterator[ResearchProviders]:
        seen.append((given, web))
        try:
            yield research_providers
        finally:
            closed.append(True)

    monkeypatch.setattr("app.main.open_research_providers", fake_composition)
    app = create_app(settings, memory_providers=memory_providers)
    async with LifespanManager(app):
        assert app.state.research_providers is research_providers and closed == []
    assert seen == [(settings, memory_providers.web)] and closed == [True]


async def test_launcher_is_bound_to_the_runner_then_unbound_at_shutdown(
    settings: Settings, db_engine: object
) -> None:
    app = create_app(settings)
    async with LifespanManager(app):
        launcher = app.state.launcher
        assert launcher.runner is app.state.runtime.runner
    assert launcher.runner is None


def test_agent_ports_compose_memory_web_council_program_lessons_and_quiz() -> None:
    learning = LearningRuntime(object(), SessionLauncher())  # type: ignore[arg-type]
    program = ProgramRuntime(object(), object())  # type: ignore[arg-type]
    lessons = LessonsRuntime(*[object()] * 6)  # type: ignore[arg-type]
    study = study_runtimes(
        object(),  # type: ignore[arg-type]
        SessionLauncher(),
        program=program,
        memory=object(),  # type: ignore[arg-type]
    )
    ports = agent_ports(
        object(),  # type: ignore[arg-type]
        object(),  # type: ignore[arg-type]
        learning=learning,
        program=program,
        lessons=lessons,
        study=study,
    )
    assert isinstance(ports.memory, AgentMemoryGateway)
    assert isinstance(ports.web, AgentWebGateway)
    assert isinstance(ports.council, AgentCouncilStore)
    assert isinstance(ports.program, AgentProgramStore)
    assert isinstance(ports.lessons, AgentLessonStore)
    assert isinstance(ports.quiz, AgentQuizStore) and isinstance(ports.study, AgentStudyStore)
    assert study.quiz.program is program is study.study.program


async def test_learning_runtime_shares_the_launcher(settings: Settings, db_engine: object) -> None:
    app = create_app(settings)
    async with LifespanManager(app):
        assert app.state.learning.launcher is app.state.launcher
        assert app.state.learning.session_factory is app.state.session_factory
        quiz = app.state.quiz  # quiz (D101) : même lanceur, programme et mémoire
        assert quiz.launcher is app.state.launcher and quiz.program is app.state.program
        assert quiz.memory is app.state.memory


async def test_lifespan_wires_lessons_and_the_scheduler(
    settings: Settings, db_engine: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Leçons composées avant le moteur (port, validation), planificateur après lui (D91)."""
    seen: list[JobContext] = []

    async def probe(ctx: JobContext) -> None:
        seen.append(ctx)

    monkeypatch.setattr(main_module, "JOBS", [JobSpec("probe", timedelta(hours=6), probe)])
    app = create_app(settings.model_copy(update={"scheduler_enabled": True}))
    async with LifespanManager(app):
        async with asyncio.timeout(3):
            while not seen:
                await asyncio.sleep(0.01)
        assert seen[0].production is app.state.lessons
        assert seen[0].launcher is app.state.launcher
        assert app.state.program.lessons is app.state.lessons
        assert app.state.lessons.launcher is app.state.launcher
    assert len(seen) == 1


async def test_scheduler_disabled_by_setting_runs_no_job(
    settings: Settings, db_engine: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`scheduler_enabled=False` (réglage des tests d'application) : aucune tâche ne tourne."""
    seen: list[JobContext] = []

    async def probe(ctx: JobContext) -> None:
        seen.append(ctx)

    monkeypatch.setattr(main_module, "JOBS", [JobSpec("probe", timedelta(hours=6), probe)])
    assert settings.scheduler_enabled is False
    async with LifespanManager(create_app(settings)):
        await asyncio.sleep(0.05)
    assert seen == []
