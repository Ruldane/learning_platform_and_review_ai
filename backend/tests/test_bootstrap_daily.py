"""Composition du quotidien (`app.bootstrap_daily`, D160) : le radar partage la base, le lanceur
et la recherche web de l'app ; son port est celui donné au moteur ; la tâche du lundi reçoit le
radar par `JobContext.daily` ; `app.main` reste sous 300 lignes."""

from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from asgi_lifespan import LifespanManager

import app.main as main_module
from app.agents.runtime.launcher import SessionLauncher
from app.agents.tools.radar_port import NO_RADAR
from app.bootstrap import agent_ports, scheduler_context
from app.bootstrap_daily import DailyRuntimes, daily_runtimes
from app.config import Settings
from app.core.providers import MemoryProviders, PublishingProviders, ResearchProviders
from app.features.radar.service.runtime import RadarRuntime
from app.features.radar.service.store import AgentRadarStore
from app.main import create_app
from app.scheduler.registry import JOBS


async def test_lifespan_wires_the_radar_and_its_port(
    settings: Settings,
    db_engine: object,
    memory_providers: MemoryProviders,
    research_providers: ResearchProviders,
    publishing_providers: PublishingProviders,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, Any] = {}
    real = main_module.agent_runtime

    def spy(*args: Any, **kwargs: Any) -> Any:
        seen.update(kwargs)
        return real(*args, **kwargs)

    monkeypatch.setattr(main_module, "agent_runtime", spy)
    app = create_app(
        settings,
        memory_providers=memory_providers,
        research_providers=research_providers,
        publishing_providers=publishing_providers,
    )
    async with LifespanManager(app):
        daily = app.state.daily
        assert isinstance(daily, DailyRuntimes) and isinstance(daily.radar, RadarRuntime)
        assert daily.radar.launcher is app.state.launcher
        assert daily.radar.session_factory is app.state.session_factory
        assert daily.radar.research is app.state.research
        assert isinstance(daily.radar_store, AgentRadarStore)
        assert seen["ports"].radar is daily.radar_store


async def test_scheduler_gets_the_daily_runtimes(
    settings: Settings,
    db_engine: object,
    memory_providers: MemoryProviders,
    research_providers: ResearchProviders,
    publishing_providers: PublishingProviders,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[Any] = []
    real = main_module.scheduler_context

    def spy(*args: Any) -> Any:
        seen.extend(args)
        return real(*args)

    monkeypatch.setattr(main_module, "scheduler_context", spy)
    app = create_app(
        settings.model_copy(update={"scheduler_enabled": True}),
        memory_providers=memory_providers,
        research_providers=research_providers,
        publishing_providers=publishing_providers,
    )
    async with LifespanManager(app):
        assert seen[-1] is app.state.daily


def test_daily_runtimes_build_the_radar_port_on_the_same_runtime() -> None:
    daily = daily_runtimes(
        object(),  # type: ignore[arg-type]
        SessionLauncher(),
        research=object(),  # type: ignore[arg-type]
        career=object(),  # type: ignore[arg-type]
        study=object(),  # type: ignore[arg-type]
    )
    assert isinstance(daily.radar_store, AgentRadarStore)
    assert daily.radar_store._rt is daily.radar  # type: ignore[attr-defined]
    assert agent_ports.__kwdefaults__ is not None
    assert agent_ports.__kwdefaults__["radar"] is NO_RADAR


def test_job_context_carries_the_daily_runtimes() -> None:
    marker = object()
    context = scheduler_context(*(object(),) * 5, marker)  # type: ignore[arg-type, misc]
    assert context.daily is marker


def test_the_radar_task_runs_every_fifteen_minutes_and_at_startup() -> None:
    [spec] = [job for job in JOBS if job.name == "market_radar"]
    assert spec.every == timedelta(minutes=15) and spec.at_startup


def test_main_stays_under_the_length_limit() -> None:
    main = Path(main_module.__file__)
    assert len(main.read_text(encoding="utf-8").splitlines()) <= 300
