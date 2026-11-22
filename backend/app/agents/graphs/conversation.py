from typing import Any
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from app.agents.nodes.conversation import ConversationState, make_reply, make_save
from app.agents.runtime.deps import GraphDeps


class ConversationInput(BaseModel):
    thread_id: UUID
    turn_id: UUID


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    graph = StateGraph(ConversationState)
    graph.add_node("reply", make_reply(deps))
    graph.add_node("save", make_save(deps))
    graph.add_edge(START, "reply")
    graph.add_edge("reply", "save")
    graph.add_edge("save", END)
    return graph
