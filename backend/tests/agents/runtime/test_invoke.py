import asyncio
from typing import Any

import httpx
import openai
import pytest
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from app.agents.runtime import invoke as invoke_module
from app.agents.runtime.invoke import NODE_TIMEOUT_S, RETRY_DELAYS_S, invoke_agent, node_timeout
from app.core.errors import AppError
from app.providers.llm.base import CALL_DEADLINE_KEY, LLM_CALL_DEADLINE_S, LLM_CALL_TIMEOUT_S
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
async def test_invoke_agent_gives_up_after_all_delays_with_a_readable_error(
    sleeps: list[float],
) -> None:
    model = FlakyModel(fail_times=99, exc=httpx.ConnectError("c"))
    with pytest.raises(AppError) as e:
        await invoke_agent(model, [HumanMessage("x")], agent="a", step="s", intent="i")
    assert e.value.code == "llm_unavailable"
    assert model.calls == 1 + len(RETRY_DELAYS_S) and sleeps == list(RETRY_DELAYS_S)


SDK_MESSAGE = "Incorrect API key provided: sk-proj-****cdef"
REQUEST = httpx.Request("POST", "https://exemple.test/v1/chat/completions")


def _provider_model(exc: BaseException, provider: str, label: str) -> FlakyModel:
    """Modèle qui échoue comme un SDK, avec les métadonnées posées par `build()`."""
    meta = {"tremplin_provider": provider, "tremplin_provider_label": label}
    return FlakyModel(fail_times=99, exc=exc, metadata=meta)


@pytest.mark.usefixtures("emitted")
async def test_rejected_key_fails_at_once_with_a_readable_message(
    sleeps: list[float], caplog: pytest.LogCaptureFixture
) -> None:
    response = httpx.Response(401, request=REQUEST)
    exc = openai.AuthenticationError(SDK_MESSAGE, response=response, body=None)
    model = _provider_model(exc, "openai", "OpenAI")
    with pytest.raises(AppError) as e:
        await invoke_agent(model, [HumanMessage("x")], agent="a", step="s", intent="i")
    assert e.value.code == "llm_key_rejected" and "OpenAI" in e.value.message
    assert model.calls == 1 and sleeps == []
    assert "cdef" not in e.value.message and "cdef" not in caplog.text
    assert e.value.__cause__ is None and e.value.__suppress_context__


@pytest.mark.usefixtures("emitted")
async def test_exhausted_glm_credit_is_not_retried(sleeps: list[float]) -> None:
    response = httpx.Response(429, request=REQUEST)
    exc = openai.RateLimitError(SDK_MESSAGE, response=response, body={"code": "1113"})
    model = _provider_model(exc, "glm", "GLM (Z.ai)")
    with pytest.raises(AppError) as e:
        await invoke_agent(model, [HumanMessage("x")], agent="a", step="s", intent="i")
    assert e.value.code == "llm_credit_exhausted"
    assert e.value.message == "Crédit Z.ai insuffisant pour ce modèle."
    assert model.calls == 1 and sleeps == []


@pytest.mark.usefixtures("emitted")
async def test_rate_limit_is_retried_then_reported_readably(sleeps: list[float]) -> None:
    response = httpx.Response(429, request=REQUEST)
    exc = openai.RateLimitError(SDK_MESSAGE, response=response, body=None)
    model = _provider_model(exc, "openai", "OpenAI")
    with pytest.raises(AppError) as e:
        await invoke_agent(model, [HumanMessage("x")], agent="a", step="s", intent="i")
    assert e.value.code == "llm_rate_limited"
    assert model.calls == 1 + len(RETRY_DELAYS_S)


def test_two_full_calls_and_a_retry_delay_fit_in_the_node_budget() -> None:
    # M3 : un appel qui pend laisse la place à un nouvel essai complet avant `node_timeout`.
    assert LLM_CALL_TIMEOUT_S == 45
    assert 2 * LLM_CALL_TIMEOUT_S + RETRY_DELAYS_S[0] < NODE_TIMEOUT_S


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


class HangingModel(FlakyModel):
    """Ne répond jamais (une réponse en flux qui n'en finit pas, contrôle 5.18)."""

    async def _agenerate(self, messages: Any, *args: Any, **kwargs: Any) -> Any:
        self.calls += 1
        await asyncio.Event().wait()


@pytest.mark.usefixtures("emitted")
async def test_call_deadline_cuts_a_hanging_call_then_retries(
    sleeps: list[float], caplog: pytest.LogCaptureFixture
) -> None:
    """Le délai du SDK ne borne que l'attente de chaque morceau : l'échéance totale posée par la
    fabrique coupe l'appel, qui est retenté (journal : type d'erreur seulement), puis rendu en
    `llm_timeout` lisible."""
    meta = {"tremplin_provider": "glm", "tremplin_provider_label": "GLM (Z.ai)"}
    model = HangingModel(metadata=meta | {CALL_DEADLINE_KEY: 0.02})
    with pytest.raises(AppError) as e:
        await invoke_agent(model, [HumanMessage("x")], agent="tutor", step="s", intent="i")
    assert e.value.code == "llm_timeout"
    assert model.calls == 1 + len(RETRY_DELAYS_S) and sleeps == list(RETRY_DELAYS_S)
    assert caplog.text.count("Appel LLM retenté : agent tutor") == len(RETRY_DELAYS_S)
    assert "TimeoutError" in caplog.text


@pytest.mark.usefixtures("emitted")
async def test_without_deadline_metadata_a_call_is_not_cut(sleeps: list[float]) -> None:
    model = FlakyModel(reply="ok", metadata={CALL_DEADLINE_KEY: "abc"})  # valeur ignorée
    msg = await invoke_agent(model, [HumanMessage("x")], agent="a", step="s", intent="i")
    assert msg.content == "ok" and model.calls == 1


def test_call_deadline_never_cuts_a_call_before_its_node() -> None:
    """Revue 5.18, I1 : l'échéance totale d'un appel n'est jamais plus courte que le plus long
    plafond de nœud ; sinon un appel qui aurait réussi est coupé, puis repayé sans pouvoir tenir
    dans le temps restant au nœud."""
    from app.agents.nodes.examiner import WRITE_TIMEOUT_S as EXAMINER_WRITE
    from app.agents.nodes.strategist.plan import PLAN_TIMEOUT_S
    from app.agents.nodes.writer import WRITE_TIMEOUT_S as WRITER_WRITE

    assert max(EXAMINER_WRITE, PLAN_TIMEOUT_S, WRITER_WRITE, NODE_TIMEOUT_S) <= LLM_CALL_DEADLINE_S
