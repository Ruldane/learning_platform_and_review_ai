from typing import Any

import pytest
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from app.agents.runtime.emit import EVENT_KEY, emit
from app.agents.runtime.events import AgentStartedPayload


class State(TypedDict):
    done: bool


def test_emit_outside_a_graph_raises() -> None:
    with pytest.raises(RuntimeError, match="hors d'un nœud"):
        emit("agent.started", {"step": "s", "intent": "i"})


def test_emit_validates_payload_immediately(emitted: list[dict[str, Any]]) -> None:
    with pytest.raises(ValueError, match="agent.started"):
        emit("agent.started", {"step": "s"})
    assert emitted == []


def test_emit_writes_envelope(emitted: list[dict[str, Any]]) -> None:
    emit("agent.started", AgentStartedPayload(step="s", intent="je cherche"), agent="demo")
    emit("run.completed", {})
    assert emitted == [
        {
            EVENT_KEY: "agent.started",
            "agent": "demo",
            "payload": {"step": "s", "intent": "je cherche"},
        },
        {EVENT_KEY: "run.completed", "agent": None, "payload": {"summary": ""}},
    ]


async def test_emit_reaches_the_custom_stream_of_a_real_graph() -> None:
    async def node(state: State) -> State:
        emit("agent.started", {"step": "s", "intent": "i"}, agent="demo")
        return {"done": True}

    graph = StateGraph(State)
    graph.add_node("node", node)
    graph.add_edge(START, "node")
    graph.add_edge("node", END)
    chunks = [c async for c in graph.compile().astream({"done": False}, stream_mode="custom")]
    assert chunks == [
        {EVENT_KEY: "agent.started", "agent": "demo", "payload": {"step": "s", "intent": "i"}}
    ]
