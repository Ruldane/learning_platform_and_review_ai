"""Petits parcours des tests du runner, passés au runner par `TEST_GRAPHS` (jamais enregistrés
dans `GRAPHS`). `PROBE` compte les passages dans les nœuds et synchronise les tests ; il est remis
à zéro avant chaque test (`reset_probe`)."""

import asyncio
import operator
from collections import Counter
from typing import Annotated, Any, TypedDict

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import BaseModel

from app.agents.graphs.registry import GraphSpec
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import invoke_agent, message_text
from app.agents.runtime.repositories import SessionRepository
from app.agents.runtime.structured import structured_call


class Probe:
    def __init__(self) -> None:
        self.counter: Counter[str] = Counter()
        self.b_started = asyncio.Event()
        self.release_b = asyncio.Event()
        self.b_done = asyncio.Event()


PROBE = Probe()


def reset_probe() -> Probe:
    global PROBE
    PROBE = Probe()
    return PROBE


class State(TypedDict, total=False):
    topic: str
    answer: Any
    heard: list[str]
    summary: str
    vals: Annotated[list[str], operator.add]


class NoInput(BaseModel):
    pass


class TopicInput(BaseModel):
    topic: str


def _question(text: str) -> dict[str, Any]:
    return {"kind": "choice", "question": text, "options": [{"value": "oui", "label": "Oui"}]}


def _two_steps(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    async def a(state: State) -> State:
        PROBE.counter["A"] += 1
        return {}

    async def b(state: State) -> State:
        PROBE.counter["B"] += 1
        return {"summary": "Deux étapes faites."}

    g = StateGraph(State)
    g.add_node("a", a)
    g.add_node("b", b)
    g.add_edge(START, "a")
    g.add_edge("a", "b")
    g.add_edge("b", END)
    return g


def _blocking(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    async def a(state: State) -> State:
        PROBE.counter["A"] += 1
        return {}

    async def b(state: State) -> State:
        PROBE.counter["B"] += 1
        PROBE.b_started.set()
        await PROBE.release_b.wait()
        PROBE.b_done.set()
        return {"summary": "Débloqué."}

    g = StateGraph(State)
    g.add_node("a", a)
    g.add_node("b", b)
    g.add_edge(START, "a")
    g.add_edge("a", "b")
    g.add_edge("b", END)
    return g


def _ask(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    """Pose une question, puis lit les messages de l'utilisatrice au tour suivant (D4)."""

    async def ask(state: State) -> State:
        return {"answer": interrupt(_question("On continue ?"))}

    async def after(state: State) -> State:
        PROBE.counter["after"] += 1
        heard = [text for _, text in await deps.user_messages_since(0)]
        return {"heard": heard, "summary": f"Réponse : {state['answer']}"}

    g = StateGraph(State)
    g.add_node("ask", ask)
    g.add_node("after", after)
    g.add_edge(START, "ask")
    g.add_edge("ask", "after")
    g.add_edge("after", END)
    return g


def _two_questions(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    """Deux branches parallèles qui interrompent chacune : une question à la fois."""

    def branch(name: str) -> Any:
        async def node(state: State) -> State:
            return {"vals": [f"{name}:{interrupt(_question(name))}"]}

        return node

    g = StateGraph(State)
    g.add_node("qa", branch("qa"))
    g.add_node("qb", branch("qb"))
    g.add_edge(START, "qa")
    g.add_edge(START, "qb")
    g.add_edge("qa", END)
    g.add_edge("qb", END)
    return g


def _speak(deps: GraphDeps) -> Any:
    async def speak(state: State) -> State:
        model = await deps.models.get_chat_model(deps.user_id, "rapide", agent="demo")
        reply = await invoke_agent(
            model,
            [HumanMessage(f"Parle de {state.get('topic', 'rien')}")],
            agent="demo",
            step="parole",
            intent="Je réponds",
        )
        return {"summary": message_text(reply)}

    return speak


def _one_llm_call(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    g = StateGraph(State)
    g.add_node("speak", _speak(deps))
    g.add_edge(START, "speak")
    g.add_edge("speak", END)
    return g


def _spend_then_llm(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    """Consomme tout le plafond de la session, puis tente un appel au modèle."""

    async def spend(state: State) -> State:
        async with deps.session_factory() as db:
            await SessionRepository(db, deps.user_id).add_usage(
                deps.session_id,
                tokens_in=deps.settings.session_token_cap,
                tokens_out=0,
                cost_usd=0.0,
            )
            await db.commit()
        return {}

    g = StateGraph(State)
    g.add_node("spend", spend)
    g.add_node("speak", _speak(deps))
    g.add_edge(START, "spend")
    g.add_edge("spend", "speak")
    g.add_edge("speak", END)
    return g


class Verdict(BaseModel):
    ok: bool


def _structured(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    async def judge(state: State) -> State:
        model = await deps.models.get_chat_model(deps.user_id, "rapide", agent="demo")
        verdict = await structured_call(
            model, Verdict, [HumanMessage("Juge")], agent="demo", step="juge", intent="Je juge"
        )
        return {"summary": f"ok={verdict.ok}"}

    g = StateGraph(State)
    g.add_node("judge", judge)
    g.add_edge(START, "judge")
    g.add_edge("judge", END)
    return g


SECRET = "sk-secret-a-ne-jamais-journaliser"


def _crash(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    async def boom(state: State) -> State:
        raise RuntimeError(f"panne avec {SECRET}")

    g = StateGraph(State)
    g.add_node("boom", boom)
    g.add_edge(START, "boom")
    g.add_edge("boom", END)
    return g


TEST_GRAPHS: dict[str, GraphSpec] = {
    spec.name: spec
    for spec in (
        GraphSpec("two_steps", NoInput, _two_steps),
        GraphSpec("blocking", NoInput, _blocking),
        GraphSpec("ask", NoInput, _ask),
        GraphSpec("two_questions", NoInput, _two_questions),
        GraphSpec("one_llm_call", NoInput, _one_llm_call),
        GraphSpec("with_topic", TopicInput, _one_llm_call),
        GraphSpec("spend_then_llm", NoInput, _spend_then_llm),
        GraphSpec("crash", NoInput, _crash),
        GraphSpec("structured", NoInput, _structured),
    )
}
