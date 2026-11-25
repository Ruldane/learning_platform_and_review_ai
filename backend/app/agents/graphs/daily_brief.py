"""`daily_brief` graph (P11, D161): the two sections of the morning brief that go through a
model. The block, the reviews, the follow-ups, the postings and the progress are computed by the
code (`brief` feature); here, the resource (the Scout picks among eight results of a search of the
month, the code reads the page) and the advice (two sentences from the Moderator, numbers checked
by the code): at most two quick calls.

START -> load -> resource -> advice -> close -> END

Each section re-reads the brief state through the port (`context`) and skips itself if it is
already stored: a restart before the advice does not call the Scout again. A failed section is
stored empty (`None`), never as an error: it stops neither the other one nor the end of the
graph. No interruption, no loop. Launched only by the `brief` feature (8.6, `ROUTE_ONLY`)."""

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.nodes.moderator_brief import make_advice
from app.agents.nodes.scout.brief_resource import make_resource
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.state.daily_brief import DailyBriefState, Node

__all__ = ["SUMMARY", "DailyBriefInput", "build"]

SUMMARY = "Your daily brief is ready."

logger = logging.getLogger(__name__)


class DailyBriefInput(BaseModel):
    brief_id: str = Field(min_length=36, max_length=36)


def make_load(deps: GraphDeps) -> Node:
    @node_timeout()
    async def load(state: DailyBriefState) -> DailyBriefState:
        ctx = await deps.ports.brief.context(deps.user_id, state["brief_id"])
        logger.info(
            "Brief read: session %s, brief %s, resource stored %s, advice stored %s",
            deps.session_id,
            ctx.brief_id,
            ctx.resource_done,
            ctx.advice_done,
        )
        return {}

    return load


def make_close(deps: GraphDeps) -> Node:
    @node_timeout()
    async def close(state: DailyBriefState) -> DailyBriefState:
        logger.info("Brief ready: session %s, brief %s", deps.session_id, state["brief_id"])
        return {"summary": SUMMARY}

    return close


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    graph = StateGraph(DailyBriefState)
    graph.add_node("load", make_load(deps))
    graph.add_node("resource", make_resource(deps))
    graph.add_node("advice", make_advice(deps))
    graph.add_node("close", make_close(deps))
    graph.add_edge(START, "load")
    graph.add_edge("load", "resource")
    graph.add_edge("resource", "advice")
    graph.add_edge("advice", "close")
    graph.add_edge("close", END)
    return graph
