from typing import Any

import pytest

import app.main as main_module
from app.providers.llm.fake import FakeLlmProvider
from tests.agents.runtime.runner_helpers import fake_llm_with_provider


def _script(monkeypatch: pytest.MonkeyPatch, replies: list[str]) -> FakeLlmProvider:
    llm, provider = fake_llm_with_provider(replies)
    original = main_module.agent_runtime

    def fake_runtime(*args: Any, **kwargs: Any) -> Any:
        settings, factory, _models, prices, run = args
        return original(settings, factory, llm, prices, run, **kwargs)

    monkeypatch.setattr(main_module, "agent_runtime", fake_runtime)
    return provider


@pytest.fixture
def brain_citations(monkeypatch: pytest.MonkeyPatch) -> FakeLlmProvider:
    return _script(monkeypatch, ["La note [1] complète la leçon [2]. Citation inconnue [90]."])


@pytest.fixture
def brain_history(monkeypatch: pytest.MonkeyPatch) -> FakeLlmProvider:
    return _script(
        monkeypatch,
        [
            "Constante obsolète quasar-orphelin.",
            "Constante obsolète quasar-orphelin.",
            "Vérifions les références actuelles.",
        ],
    )
