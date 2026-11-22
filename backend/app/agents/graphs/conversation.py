from typing import Any, Literal
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from app.agents.nodes.conversation import ConversationState, make_reply, make_save
from app.agents.nodes.feynman import (
    ask_clarification,
    ask_explanation,
    assess_next,
    clarified,
    explained,
    make_assessment,
    make_save_feynman,
)
from app.agents.runtime.deps import GraphDeps


class ConversationInput(BaseModel):
    thread_id: UUID
    turn_id: UUID
    feynman: bool = False


def _entry(state: ConversationState) -> Literal["reply", "explain"]:
    return "explain" if state.get("feynman") else "reply"


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    graph = StateGraph(ConversationState)
    graph.add_node("reply", make_reply(deps))
    graph.add_node("save", make_save(deps))
    graph.add_node("explain", ask_explanation)
    graph.add_node("assess", make_assessment(deps, final=False))
    graph.add_node("clarify", ask_clarification)
    graph.add_node("assess_final", make_assessment(deps, final=True))
    graph.add_node("save_feynman", make_save_feynman(deps))
    graph.add_conditional_edges(START, _entry)
    graph.add_edge("reply", "save")
    graph.add_edge("save", END)
    graph.add_conditional_edges("explain", explained, {True: "assess", False: "explain"})
    graph.add_conditional_edges("assess", assess_next)
    graph.add_conditional_edges("clarify", clarified, {True: "assess_final", False: "clarify"})
    graph.add_edge("assess_final", "save_feynman")
    graph.add_edge("save_feynman", END)
    return graph
