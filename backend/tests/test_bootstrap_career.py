"""Composition de la carrière (`app.bootstrap_career`, preflight G17, D122, D124) : les offres et le
profil maître partagent la base, le lanceur, la recherche web, la mémoire et la mise en page de
l'app ; les ports de l'écart et du profil donnés au moteur sont ceux de `app.state.career`."""

from typing import Any

import pytest
from asgi_lifespan import LifespanManager

import app.main as main_module
from app.agents.runtime.launcher import SessionLauncher
from app.agents.tools.cv_template_port import NO_CV_TEMPLATES
from app.agents.tools.gap_port import NO_GAP
from app.agents.tools.profile_port import NO_PROFILE
from app.bootstrap import agent_ports
from app.bootstrap_career import career_runtimes
from app.config import Settings
from app.core.providers import MemoryProviders, PublishingProviders, ResearchProviders
from app.features.cv.service.profile_store import AgentProfileStore
from app.features.cv.service.templates_store import AgentCvTemplateStore
from app.features.postings.service.agent_store import AgentGapStore
from app.main import create_app
from tests.support.memory import fake_publishing_providers


async def test_lifespan_wires_postings_and_the_gap_port(
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
        postings = app.state.career.postings
        assert postings.launcher is app.state.launcher
        assert postings.session_factory is app.state.session_factory
        assert postings.research is app.state.research and postings.memory is app.state.memory
        assert isinstance(app.state.career.gap, AgentGapStore)
        assert seen["ports"].gap is app.state.career.gap
        cv = app.state.career.cv
        assert cv.launcher is app.state.launcher and cv.memory is app.state.memory
        assert cv.layout is app.state.publishing_providers.layout
        assert isinstance(app.state.career.profile, AgentProfileStore)
        assert seen["ports"].profile is app.state.career.profile
        assert cv.html_pdf is app.state.publishing_providers.html_pdf
        assert cv.fonts is app.state.publishing_providers.fonts
        assert isinstance(app.state.career.cv_templates, AgentCvTemplateStore)
        assert seen["ports"].cv_templates is app.state.career.cv_templates


def test_agent_ports_default_to_no_gap() -> None:
    career = career_runtimes(
        object(),  # type: ignore[arg-type]
        SessionLauncher(),
        research=object(),  # type: ignore[arg-type]
        memory=object(),  # type: ignore[arg-type]
        publishing=fake_publishing_providers(),
    )
    assert isinstance(career.gap, AgentGapStore)
    assert isinstance(career.profile, AgentProfileStore)
    assert agent_ports.__kwdefaults__ is not None
    assert agent_ports.__kwdefaults__["gap"] is NO_GAP
    assert agent_ports.__kwdefaults__["profile"] is NO_PROFILE
    assert agent_ports.__kwdefaults__["cv_templates"] is NO_CV_TEMPLATES
    assert isinstance(career.cv_templates, AgentCvTemplateStore)
