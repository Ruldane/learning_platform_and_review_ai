"""`application_kit` graph (SPEC 6.4, F16, D142): the application kit, seven pieces written in
parallel, each one checked by the code (no fact that the profile does not state).

START -> load -> (one branch per piece not guarded) -> close -> END
branches: cv, letter, linkedin, followups, form_answers, pitch (Tracker), company_brief
(Scout, `dossier` mode)

The branches run in the same superstep: a stored piece is announced (`artifact.ready`,
`kind = "kit_item"`) as soon as it is ready, without waiting for the others. A failed piece does
not stop the others. The pieces January edited (`KitContext.keep`) are never redone: no branch
for them. `close` publishes `run.completed` with the piece count. Launched only by the route of
the `applications` feature (7.6, `ROUTE_ONLY`); every port write is idempotent (SPEC 9.4)."""

from typing import Any

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.nodes.scout.dossier import make_dossier
from app.agents.nodes.tracker.kit_common import close, make_load, route_pieces
from app.agents.nodes.tracker.pieces import make_cv, make_text_piece
from app.agents.runtime.deps import GraphDeps
from app.agents.state.application_kit import ApplicationKitState
from app.agents.tools.kit_schema import KIT_KINDS

__all__ = ["ApplicationKitInput", "build"]


class ApplicationKitInput(BaseModel):
    application_id: str = Field(min_length=36, max_length=36)


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    graph = StateGraph(ApplicationKitState)
    graph.add_node("load", make_load(deps))
    nodes: dict[str, Any] = {
        "cv": make_cv(deps),
        "company_brief": make_dossier(deps),
        **{
            kind: make_text_piece(deps, kind)
            for kind in ("letter", "linkedin", "followups", "form_answers", "pitch")
        },
    }
    if set(nodes) != set(KIT_KINDS):
        raise ValueError("Every kit piece must have its branch.")
    for name, node in nodes.items():
        graph.add_node(name, node)
        graph.add_edge(name, "close")
    graph.add_node("close", close)
    graph.add_edge(START, "load")
    graph.add_conditional_edges("load", route_pieces, [*KIT_KINDS, "close"])
    graph.add_edge("close", END)
    return graph
