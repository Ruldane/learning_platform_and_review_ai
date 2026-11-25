"""Graph `application_intake` (SPEC 6.1, 6.3, F5, D141): "I applied to X yesterday for the
role Y" becomes an application record, confirmed by January before it is created.

START -> load -> parse -> alerts -> ask
ask -> (invalid answer: ask) | (create, distinct: save) | (cancel, open: leave)
save -> announce -> END ; leave -> END

`ask` asks "Create this record?" via `interrupt()` (alone in its node, SPEC 9.4)
with the duplicate alert if there is one; `save` creates the record through the port, idempotent per
session. Started only by the `applications` feature route (`ROUTE_ONLY`), which checks
that no other intake session is open."""

from typing import Any

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.nodes.tracker import (
    announce,
    ask_confirm,
    leave,
    make_alerts,
    make_load,
    make_parse,
    make_save,
    route_confirm,
)
from app.agents.runtime.deps import GraphDeps
from app.agents.state.application_intake import ApplicationIntakeState

__all__ = ["ApplicationIntakeInput", "build"]

TEXT_MAX = 1000


class ApplicationIntakeInput(BaseModel):
    text: str = Field(min_length=1, max_length=TEXT_MAX)


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    graph = StateGraph(ApplicationIntakeState)
    graph.add_node("load", make_load(deps))
    graph.add_node("parse", make_parse(deps))
    graph.add_node("alerts", make_alerts(deps))
    graph.add_node("ask", ask_confirm)
    graph.add_node("save", make_save(deps))
    graph.add_node("announce", announce)
    graph.add_node("leave", leave)
    for source, target in [
        (START, "load"),
        ("load", "parse"),
        ("parse", "alerts"),
        ("alerts", "ask"),
        ("save", "announce"),
        ("announce", END),
        ("leave", END),
    ]:
        graph.add_edge(source, target)
    graph.add_conditional_edges("ask", route_confirm, ["ask", "save", "leave"])
    return graph
