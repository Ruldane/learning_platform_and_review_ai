"""Graph `web_research` (D77): the Scout searches the web, reads, rates each source out of 100
and keeps the selected ones in memory (SPEC 10). Test bench of web search, reused as is
by the Council in phase 4. No interruption.

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
from app.agents.nodes.scout.models import MAX_EXTRA_URLS
from app.agents.runtime.deps import GraphDeps
from app.agents.state.web_research import WebResearchState


class WebResearchInput(BaseModel):
    query: str = Field(min_length=2, max_length=300)
    urls: list[HttpUrl] = Field(default_factory=list, max_length=MAX_EXTRA_URLS)  # on top


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
