import pytest
from pydantic import BaseModel

from app.agents.graphs.registry import GRAPHS, GraphSpec, get_graph
from app.agents.prompts.loader import PROMPTS_DIR
from app.agents.registry import AGENTS, AgentSpec, get_agent
from app.core.errors import AppError


def test_get_graph_unknown_raises_app_error() -> None:
    with pytest.raises(AppError) as e:
        get_graph("nope")
    assert e.value.code == "unknown_graph" and e.value.status_code == 404
    assert e.value.message == "Parcours inconnu : nope"


def test_get_agent_unknown_raises_app_error() -> None:
    with pytest.raises(AppError) as e:
        get_agent("nope")
    assert e.value.code == "unknown_agent" and e.value.status_code == 404


def test_registries_return_registered_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    class Input(BaseModel):
        topic: str

    agent = AgentSpec(name="demo", tier="rapide")
    graph = GraphSpec(name="g", input_model=Input, build=lambda deps: None)  # type: ignore[arg-type, return-value]
    monkeypatch.setitem(AGENTS, "demo", agent)
    monkeypatch.setitem(GRAPHS, "g", graph)
    assert get_agent("demo") is agent
    assert get_graph("g") is graph


def test_every_registered_agent_has_a_prompt_file() -> None:
    for name in AGENTS:
        assert (PROMPTS_DIR / f"{name}.md").is_file()


def test_registered_names_match_their_keys() -> None:
    assert all(key == spec.name for key, spec in AGENTS.items())
    assert all(key == spec.name for key, spec in GRAPHS.items())
