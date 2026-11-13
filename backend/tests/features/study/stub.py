"""Parcours `study_session` de test, sans modèle : lit la séance par le vrai port (`context`),
pose une question (`tutor_question`) jusqu'à « Terminer », puis range la fin par le vrai port
(`finish`) avec un résultat choisi (`STUB.outcome`). `STUB.hold` fige le premier nœud (le
Tuteur « écrit ») ; `STUB.fail` fait échouer la session en route. Monté sur le vrai moteur du
lifespan (`install`, avant le lifespan)."""

import asyncio
from dataclasses import asdict, dataclass, field
from typing import Any, TypedDict

import pytest
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.agents.graphs.registry import GRAPHS, GraphSpec
from app.agents.graphs.study_session import StudySessionInput
from app.agents.runtime.deps import GraphDeps
from app.agents.tools.study_port import Outcome, StudyOutcome
from tests.sessions_support import use_test_runtime

QUESTION = "Que fait la softmax ?"


def full_outcome(*, ended_early: bool = False, exercise: str = "partial") -> StudyOutcome:
    outcomes = [
        Outcome("section", 0, QUESTION, "Elle normalise les scores.", "correct", 0),
        Outcome("section", 1, "Pourquoi la racine ?", "Pour stabiliser.", "wrong", 1),
        Outcome("exercise", 0, "Calcule la softmax.", "Environ [0,27 ; 0,73].", exercise, 0),  # type: ignore[arg-type]
        Outcome("final", 0, "Que cache le masque ?", "Le futur.", "revealed", 3),
        Outcome("final", 1, "Question passée ?", "Réponse passée.", "skipped", 0),
    ]
    return StudyOutcome(
        outcomes=outcomes,
        exercise_done=exercise in ("correct", "partial"),
        ended_early=ended_early,
        summary="Bonne séance : la softmax est acquise.",
    )


@dataclass
class StubControl:
    outcome: StudyOutcome = field(default_factory=full_outcome)
    hold: asyncio.Event | None = None
    fail: bool = False
    contexts: list[Any] = field(default_factory=list)
    finished: list[Any] = field(default_factory=list)

    def reset(self) -> None:
        self.outcome, self.hold, self.fail = full_outcome(), None, False
        self.contexts, self.finished = [], []


STUB = StubControl()


class StubState(TypedDict, total=False):
    study_session_id: str
    reply: Any


def _build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    async def open_(state: StubState) -> StubState:
        found = await deps.ports.study.context(deps.user_id, state["study_session_id"])
        STUB.contexts.append(found)
        if STUB.hold is not None:
            await STUB.hold.wait()
        if STUB.fail:
            raise RuntimeError("panne du Tuteur")
        return {}

    def ask(state: StubState) -> StubState:
        return {
            "reply": interrupt(
                {
                    "kind": "tutor_question",
                    "question": QUESTION,
                    "options": [{"value": "skip", "label": "Passer"}],
                    "fields": [{"id": "answer", "label": "Ta réponse", "max_length": 4000}],
                }
            )
        }

    def route(state: StubState) -> str:
        return "wrap" if state.get("reply") == {"action": "finish"} else "ask"

    async def wrap(state: StubState) -> StubState:
        done = await deps.ports.study.finish(
            deps.user_id, deps.session_id, state["study_session_id"], STUB.outcome
        )
        STUB.finished.append(asdict(done))
        return {}

    graph = StateGraph(StubState)
    graph.add_node("open", open_)
    graph.add_node("ask", ask)
    graph.add_node("wrap", wrap)
    graph.add_edge(START, "open")
    graph.add_edge("open", "ask")
    graph.add_conditional_edges("ask", route, ["ask", "wrap"])
    graph.add_edge("wrap", END)
    return graph


def install(monkeypatch: pytest.MonkeyPatch) -> StubControl:
    """Parcours de test dans le registre, faux LLM : à appeler avant le lifespan."""
    use_test_runtime(monkeypatch)
    spec = GraphSpec("study_session", StudySessionInput, _build)
    monkeypatch.setitem(GRAPHS, "study_session", spec)
    STUB.reset()
    return STUB
