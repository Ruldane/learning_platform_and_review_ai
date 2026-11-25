"""Graph `market_radar` (P5, P6, D159): the job market survey. The Scout searches
the month's offers and reads them in passes of ten links; the Analyst extracts skills, tools,
level and salary in batches of five; ranking, trends and alerts are computed by the
code, ailleurs (feature `radar`).

START -> load -> search -> read (boucle) -> extract (boucle) -> finish -> END

Two loops per conditional edge (no routing node: each pass is one step of the
graph). Each one rereads the survey state through the port on every pass; a restart does not reread
or re-extract anything. Worst case: 6 read passes (60 reads) and 10 extraction passes (50 offers),
i.e. 19 steps. `recursion_limit` (LangGraph step limit; documented default 10,007 since
1.1.4, not 25) is therefore never reached; the start (8.4) still sets it to
6 + 2 × (60 / 10 + 50 / 5) = 38 so that an endless loop fails fast. No interruption.
Started only by the `radar` feature route (8.4, `ROUTE_ONLY`)."""

from typing import Any

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.nodes.analyst_radar import make_extract, route_extract
from app.agents.nodes.scout.radar import (
    make_finish,
    make_load,
    make_read,
    make_search,
    route_read,
)
from app.agents.runtime.deps import GraphDeps
from app.agents.state.market_radar import MarketRadarState

__all__ = ["RECURSION_LIMIT", "MarketRadarInput", "build"]

# 6 fixed steps (loading, search, end, margin) + 2 × (60 reads / 10 + 50 offers / 5), D159.
RECURSION_LIMIT = 6 + 2 * (60 // 10 + 50 // 5)


class MarketRadarInput(BaseModel):
    run_id: str = Field(min_length=36, max_length=36)


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    graph = StateGraph(MarketRadarState)
    graph.add_node("load", make_load(deps))
    graph.add_node("search", make_search(deps))
    graph.add_node("read", make_read(deps))
    graph.add_node("extract", make_extract(deps))
    graph.add_node("finish", make_finish(deps))
    graph.add_edge(START, "load")
    graph.add_edge("load", "search")
    graph.add_edge("search", "read")
    graph.add_conditional_edges("read", route_read, ["read", "extract"])
    graph.add_conditional_edges("extract", route_extract, ["extract", "finish"])
    graph.add_edge("finish", END)
    return graph
