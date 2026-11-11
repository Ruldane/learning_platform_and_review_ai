import asyncio
from typing import Any

import httpx
import pytest
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from app.agents.runtime import invoke as invoke_module
from app.agents.runtime.invoke import RETRY_DELAYS_S, invoke_agent, node_timeout
from app.core.errors import AppError
from tests.agents.runtime.fakes import FlakyModel, fake_model


@pytest.fixture
def sleeps(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    slept: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr(invoke_module, "_sleep", fake_sleep)
    return slept


@pytest.mark.usefixtures("emitted")
async def test_invoke_agent_retries_transient_errors(sleeps: list[float]) -> None:
    model = FlakyModel(fail_times=2, exc=httpx.ReadTimeout("t"), reply="ok")
    msg = await invoke_agent(
        model, [HumanMessage("x")], agent="demo_critic", step="t1", intent="je réfléchis"
    )
    assert msg.content == "ok" and model.calls == 3
    assert sleeps == [1.0, 2.0]


@pytest.mark.usefixtures("emitted")
async def test_invoke_agent_gives_up_after_all_delays(sleeps: list[float]) -> None:
    model = FlakyModel(fail_times=99, exc=httpx.ConnectError("c"))
    with pytest.raises(httpx.ConnectError):
        await invoke_agent(model, [HumanMessage("x")], agent="a", step="s", intent="i")
    assert model.calls == 1 + len(RETRY_DELAYS_S) and sleeps == list(RETRY_DELAYS_S)


@pytest.mark.usefixtures("emitted")
async def test_invoke_agent_does_not_retry_non_transient(sleeps: list[float]) -> None:
    model = FlakyModel(fail_times=1, exc=ValueError("x"))
    with pytest.raises(ValueError):
        await invoke_agent(model, [HumanMessage("x")], agent="a", step="s", intent="i")
    assert model.calls == 1 and sleeps == []


async def test_invoke_agent_emits_started_then_message(emitted: list[dict[str, Any]]) -> None:
    model, _ = fake_model(["Bonjour le monde"])
    msg = await invoke_agent(model, [HumanMessage("x")], agent="demo", step="t1", intent="je salue")
    assert [e["__tremplin_event__"] for e in emitted] == ["agent.started", "agent.message"]
    assert emitted[0]["payload"] == {"step": "t1", "intent": "je salue"}
    assert emitted[1]["agent"] == "demo"
    assert emitted[1]["payload"]["text"] == "Bonjour le monde"  # type: ignore[index]
    assert emitted[1]["payload"]["message_id"] == msg.id  # type: ignore[index]


@pytest.mark.usefixtures("emitted")
async def test_invoke_agent_retries_empty_replies_then_fails_readably(sleeps: list[float]) -> None:
    # GLM renvoie parfois un `content` vide (réflexion seule) : on retente, puis erreur lisible.
    model = FlakyModel(reply="  ")
    with pytest.raises(AppError) as e:
        await invoke_agent(model, [HumanMessage("x")], agent="demo", step="s", intent="i")
    assert e.value.code == "llm_empty_reply" and "demo" in e.value.message
    assert model.calls == 1 + len(RETRY_DELAYS_S)


@pytest.mark.usefixtures("emitted")
async def test_invoke_agent_recovers_when_a_retry_returns_content(sleeps: list[float]) -> None:
    model, _ = fake_model(["", "enfin"])
    msg = await invoke_agent(model, [HumanMessage("x")], agent="a", step="s", intent="i")
    assert msg.content == "enfin" and sleeps == [1.0]


class State(TypedDict):
    done: bool


@pytest.mark.usefixtures("emitted")
async def test_invoke_agent_tags_the_call_with_the_agent_and_inherits_callbacks() -> None:
    seen: list[tuple[list[str] | None, dict[str, Any] | None]] = []

    class Spy(AsyncCallbackHandler):
        async def on_chat_model_start(  # type: ignore[override]
            self,
            serialized: Any,
            messages: Any,
            *,
            tags: list[str] | None = None,
            metadata: dict[str, Any] | None = None,
            **kwargs: Any,
        ) -> None:
            seen.append((tags, metadata))

    model, _ = fake_model(["ok"])

    async def node(state: State) -> State:
        await invoke_agent(model, [HumanMessage("x")], agent="demo_critic", step="s", intent="i")
        return {"done": True}

    graph = StateGraph(State)
    graph.add_node("node", node)
    graph.add_edge(START, "node")
    graph.add_edge("node", END)
    await graph.compile().ainvoke({"done": False}, config={"callbacks": [Spy()]})
    tags, metadata = seen[0]
    assert tags is not None and "agent:demo_critic" in tags
    assert metadata is not None and metadata["agent"] == "demo_critic"
    assert metadata["tremplin_provider"] == "fake"  # le modèle garde ses propres métadonnées


async def test_node_timeout_raises_readable_error() -> None:
    @node_timeout(0.01)
    async def slow(state: dict[str, Any]) -> dict[str, Any]:
        await asyncio.sleep(1)
        return {}

    with pytest.raises(AppError) as e:
        await slow({})
    assert e.value.code == "node_timeout"
    assert e.value.message == "L'étape slow a dépassé 0.01 secondes."


async def test_node_timeout_keeps_result_and_signature() -> None:
    @node_timeout()
    async def fast(state: dict[str, Any], config: Any = None) -> dict[str, Any]:
        """Doc."""
        return {"ok": state["x"]}

    assert await fast({"x": 1}) == {"ok": 1}
    assert fast.__name__ == "fast" and fast.__doc__ == "Doc."
    assert invoke_module.NODE_TIMEOUT_S == 120
