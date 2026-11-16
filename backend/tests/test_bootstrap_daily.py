"""Composition du quotidien (`app.bootstrap_daily`, D160, D162, D166) : le radar partage la base, le
lanceur et la recherche web de l'app ; le brief, les quiz, l'étude et les candidatures ; les
projets, la mémoire, le stockage et le profil maître ; leurs ports sont ceux donnés au moteur ;
les tâches reçoivent le quotidien par `JobContext.daily` ; `app.main` reste sous 300 lignes."""

from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from asgi_lifespan import LifespanManager

import app.main as main_module
from app.agents.runtime.launcher import SessionLauncher
from app.agents.tools.brief_port import NO_BRIEF
from app.agents.tools.project_port import NO_PROJECTS
from app.agents.tools.radar_port import NO_RADAR
from app.bootstrap import agent_ports, scheduler_context
from app.bootstrap_daily import DailyRuntimes, daily_runtimes
from app.config import Settings
from app.core.providers import MemoryProviders, PublishingProviders, ResearchProviders
from app.features.brief.service.runtime import BriefRuntime
from app.features.brief.service.store import AgentBriefStore
from app.features.projects.service.runtime import ProjectsRuntime
from app.features.projects.service.store import AgentProjectStore
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
        assert isinstance(daily.brief, BriefRuntime) and isinstance(
            daily.brief_store, AgentBriefStore
        )
        assert seen["ports"].brief is daily.brief_store
        assert daily.brief.launcher is app.state.launcher
        assert daily.brief.session_factory is app.state.session_factory
        assert daily.brief.quiz is app.state.quiz and daily.brief.study is app.state.study
        assert daily.brief.applications is app.state.career.applications
        assert isinstance(daily.projects, ProjectsRuntime)
        assert isinstance(daily.project_store, AgentProjectStore)
        assert seen["ports"].projects is daily.project_store
        assert daily.projects.launcher is app.state.launcher
        assert daily.projects.session_factory is app.state.session_factory
        assert daily.projects.research is app.state.research
        assert (
            daily.projects.memory is app.state.memory and daily.projects.cv is app.state.career.cv
        )
        assert daily.projects.storage is app.state.memory_providers.storage


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


def test_daily_runtimes_build_the_ports_on_the_same_runtimes() -> None:
    quiz, study, applications = object(), object(), object()
    cv = SimpleNamespace(storage=object(), memory=object())
    daily = daily_runtimes(
        object(),  # type: ignore[arg-type]
        SessionLauncher(),
        research=object(),  # type: ignore[arg-type]
        career=SimpleNamespace(applications=applications, cv=cv),  # type: ignore[arg-type]
        study=SimpleNamespace(quiz=quiz, study=study),  # type: ignore[arg-type]
    )
    assert isinstance(daily.radar_store, AgentRadarStore)
    assert daily.radar_store._rt is daily.radar  # type: ignore[attr-defined]
    assert isinstance(daily.brief_store, AgentBriefStore)
    assert daily.brief_store._rt is daily.brief  # type: ignore[attr-defined]
    assert (daily.brief.quiz, daily.brief.study) == (quiz, study)
    assert daily.brief.applications is applications
    assert isinstance(daily.project_store, AgentProjectStore)
    assert daily.project_store._rt is daily.projects  # type: ignore[attr-defined]
    assert (daily.projects.storage, daily.projects.memory) == (cv.storage, cv.memory)
    assert daily.projects.cv is cv
    assert agent_ports.__kwdefaults__ is not None
    assert agent_ports.__kwdefaults__["radar"] is NO_RADAR
    assert agent_ports.__kwdefaults__["brief"] is NO_BRIEF
    assert agent_ports.__kwdefaults__["projects"] is NO_PROJECTS


def test_job_context_carries_the_daily_runtimes() -> None:
    marker = object()
    context = scheduler_context(*(object(),) * 5, marker)  # type: ignore[arg-type, misc]
    assert context.daily is marker


def test_the_radar_task_runs_every_fifteen_minutes_and_at_startup() -> None:
    [spec] = [job for job in JOBS if job.name == "market_radar"]
    assert spec.every == timedelta(minutes=15) and spec.at_startup


def test_the_brief_task_runs_every_ten_minutes_and_at_startup() -> None:
    [spec] = [job for job in JOBS if job.name == "daily_brief"]
    assert spec.every == timedelta(minutes=10) and spec.at_startup


def test_the_project_task_runs_every_fifteen_minutes_and_at_startup() -> None:
    [spec] = [job for job in JOBS if job.name == "project_briefs"]
    assert spec.every == timedelta(minutes=15) and spec.at_startup


def test_main_stays_under_the_length_limit() -> None:
    main = Path(main_module.__file__)
    assert len(main.read_text(encoding="utf-8").splitlines()) <= 300
