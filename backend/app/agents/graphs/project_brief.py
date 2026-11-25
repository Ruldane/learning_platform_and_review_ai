"""Graph `project_brief` (P1, D165): the Practitioner writes the brief of a module's
mini project (one standard call, 3 to 6 criteria a reviewer can check).

START -> load -> write -> save -> close -> END

No interruption, no loop. Invalid output stores the failure through the port
(`brief_failed("structured_output_invalid")`) and stops the graph: `run.failed` gives the cause,
"Retry" restarts it. The port write is idempotent per session (SPEC 9.4). Started only
by the `projects` feature (8.10, `ROUTE_ONLY`)."""

from typing import Any

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.nodes.practitioner.brief import (
    SUMMARY,
    make_close,
    make_load,
    make_save,
    make_write,
)
from app.agents.runtime.deps import GraphDeps
from app.agents.state.project_brief import ProjectBriefState

__all__ = ["SUMMARY", "ProjectBriefInput", "build"]


class ProjectBriefInput(BaseModel):
    project_id: str = Field(min_length=36, max_length=36)


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    graph = StateGraph(ProjectBriefState)
    graph.add_node("load", make_load(deps))
    graph.add_node("write", make_write(deps))
    graph.add_node("save", make_save(deps))
    graph.add_node("close", make_close(deps))
    graph.add_edge(START, "load")
    graph.add_edge("load", "write")
    graph.add_edge("write", "save")
    graph.add_edge("save", "close")
    graph.add_edge("close", END)
    return graph
