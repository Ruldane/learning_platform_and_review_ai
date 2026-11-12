"""Parcours `web_research` (D77) : l'Éclaireur cherche sur le web, lit, note chaque source sur 100
et garde les retenues en mémoire (SPEC 10). Banc d'essai de la recherche web, réutilisé tel quel
par le Conseil en phase 4. Aucune interruption.

START -> plan -> search -> read -> judge -> remember -> finalize -> END
"""

from typing import Any

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, HttpUrl

from app.agents.nodes.scout import (
    finalize,
    make_judge,
    make_plan,
    make_read,
    make_remember,
    make_search,
)
from app.agents.runtime.deps import GraphDeps
from app.agents.state.web_research import WebResearchState


class WebResearchInput(BaseModel):
    query: str = Field(min_length=2, max_length=300)
    urls: list[HttpUrl] = Field(default_factory=list, max_length=5)  # pages à lire en plus


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    graph = StateGraph(WebResearchState)
    graph.add_node("plan", make_plan(deps))
    graph.add_node("search", make_search(deps))
    graph.add_node("read", make_read(deps))
    graph.add_node("judge", make_judge(deps))
    graph.add_node("remember", make_remember(deps))
    graph.add_node("finalize", finalize)
    graph.add_edge(START, "plan")
    graph.add_edge("plan", "search")
    graph.add_edge("search", "read")
    graph.add_edge("read", "judge")
    graph.add_edge("judge", "remember")
    graph.add_edge("remember", "finalize")
    graph.add_edge("finalize", END)
    return graph
