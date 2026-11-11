"""Parcours de démonstration `demo_debate` : le Défenseur et le Critique débattent d'un sujet ;
entre deux tours, l'utilisatrice choisit l'angle du suivant (point d'arrêt `interrupt`).

START -> proponent -> critic -> (ask_user -> proponent -> critic)* -> finalize -> END
Le nombre de tours est le réglage `debate_rounds` de l'utilisatrice.
"""

from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import BaseModel, Field

from app.agents.nodes.demo_critic import make_critic
from app.agents.nodes.demo_proponent import make_proponent
from app.agents.runtime.deps import GraphDeps
from app.agents.state.demo_debate import DemoDebateState

ANGLES = {"concret": "Plus concret", "court": "Plus court"}


class DemoDebateInput(BaseModel):
    topic: str = Field(min_length=3, max_length=200)


def _question(next_round: int) -> str:
    which = "le second tour" if next_round == 2 else f"le tour {next_round}"
    return f"Quel angle pour {which} ?"


def _ask_user(state: DemoDebateState) -> DemoDebateState:
    # Rien avant `interrupt()` : le nœud est rejoué depuis son début à la reprise.
    choice = interrupt(
        {
            "kind": "choice",
            "question": _question(state.get("round", 0) + 1),
            "options": [{"value": v, "label": label} for v, label in ANGLES.items()],
        }
    )
    return {"user_choice": str(choice)}


def _finalize(state: DemoDebateState) -> DemoDebateState:
    angle = ANGLES.get(state.get("user_choice") or "", "libre")
    return {
        "summary": (
            f"Débat sur « {state['topic']} » en {state.get('round', 0)} tour(s), "
            f"{len(state.get('turns', []))} répliques. Dernier angle choisi : {angle}."
        )
    }


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    def after_critic(state: DemoDebateState) -> str:
        return "ask_user" if state.get("round", 0) < deps.settings.debate_rounds else "finalize"

    graph = StateGraph(DemoDebateState)
    graph.add_node("proponent", make_proponent(deps))
    graph.add_node("critic", make_critic(deps))
    graph.add_node("ask_user", _ask_user)
    graph.add_node("finalize", _finalize)
    graph.add_edge(START, "proponent")
    graph.add_edge("proponent", "critic")
    graph.add_conditional_edges("critic", after_critic, ["ask_user", "finalize"])
    graph.add_edge("ask_user", "proponent")
    graph.add_edge("finalize", END)
    return graph
