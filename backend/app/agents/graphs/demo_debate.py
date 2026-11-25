"""Demo graph `demo_debate`: the Defender and the Critic debate a topic;
between two turns, the user picks the angle of the next one (break point `interrupt`).

START -> proponent -> critic -> (ask_user -> proponent -> critic)* -> finalize -> END
The number of turns is the user's `debate_rounds` setting.
"""

from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import BaseModel, Field

from app.agents.nodes.demo_critic import make_critic
from app.agents.nodes.demo_proponent import make_proponent
from app.agents.runtime.deps import GraphDeps
from app.agents.state.demo_debate import DemoDebateState

ANGLES = {"concret": "More concrete", "court": "Shorter"}


class DemoDebateInput(BaseModel):
    topic: str = Field(min_length=3, max_length=200)


def _question(next_round: int) -> str:
    return f"What approach should we take in round {next_round}?"


def _ask_user(state: DemoDebateState) -> DemoDebateState:
    # Nothing before `interrupt()`: the node is replayed from its start on resume.
    choice = interrupt(
        {
            "kind": "choice",
            "question": _question(state.get("round", 0) + 1),
            "options": [{"value": v, "label": label} for v, label in ANGLES.items()],
        }
    )
    return {"user_choice": str(choice)}


def _finalize(state: DemoDebateState) -> DemoDebateState:
    angle = ANGLES.get(state.get("user_choice") or "", "open discussion")
    return {
        "summary": (
            f"Debate on “{state['topic']}” finished after {state.get('round', 0)} rounds "
            f"and {len(state.get('turns', []))} responses. Final approach was {angle}."
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
