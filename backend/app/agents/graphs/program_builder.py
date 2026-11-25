"""Graph `program_builder` (SPEC 3.1 step 7, 3.4, D86): the Strategist builds the program
week by week from the path chosen at the Council, then January validates it (break point
no. 3) or asks for a revision (new version, current plan reread from the database).

START -> context -> draft -> save -> ask_validation -> route_validation
route_validation : validate -> finalize -> END ; revise -> draft (revision + 1, note) ;
                   invalid answer -> ask_validation
"""

from datetime import date
from typing import Any

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.nodes.strategist.plan import (
    ask_validation,
    make_context,
    make_draft,
    make_finalize,
    make_save,
    route_validation,
)
from app.agents.runtime.deps import GraphDeps
from app.agents.state.program_builder import ProgramState


class ProgramBuilderInput(BaseModel):
    goal_id: str = Field(min_length=36, max_length=36)
    proposal_ids: list[str] = Field(min_length=1, max_length=2)
    start_date: date | None = None


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    graph = StateGraph(ProgramState)
    graph.add_node("context", make_context(deps))
    graph.add_node("draft", make_draft(deps))
    graph.add_node("save", make_save(deps))
    graph.add_node("ask_validation", ask_validation)
    graph.add_node("finalize", make_finalize(deps))
    for source, target in [
        (START, "context"),
        ("context", "draft"),
        ("draft", "save"),
        ("save", "ask_validation"),
        ("finalize", END),
    ]:
        graph.add_edge(source, target)
    graph.add_conditional_edges(
        "ask_validation", route_validation, ["ask_validation", "draft", "finalize"]
    )
    return graph
