"""Graph `interview` (SPEC F10, 9.4, D145): a written mock interview led by the Interviewer.

START -> load -> plan -> ask
ask -> (unreadable answer: ask) | (answer: turn) | ("End the interview": debrief)
turn -> (follow-up or next question: ask) | (no more questions: debrief)
debrief -> save -> END

`ask` asks the question with `interrupt()` (alone in its node, SPEC 9.4); the plan, the current
question and the exchanges live in the state (checkpointer): a restart while waiting asks the
same question again without asking the model anything. One follow-up at most per question. "End"
after at least one answer: debrief on the answered questions; before any answer: `save`
stores a stopped interview, without debrief. `save` is the only write, idempotent per session.
Started only by the `applications` feature route (7.9, `ROUTE_ONLY`)."""

from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.nodes.interviewer import (
    ask,
    make_debrief,
    make_load,
    make_plan,
    make_save,
    make_turn,
    route_ask,
    route_turn,
)
from app.agents.nodes.interviewer.system_design import (
    ask_design,
    design_submitted,
    make_review_design,
    make_save_design,
)
from app.agents.runtime.deps import GraphDeps
from app.agents.state.interview import InterviewState

__all__ = ["InterviewInput", "build"]


class InterviewInput(BaseModel):
    interview_id: str = Field(min_length=36, max_length=36)
    system_design: bool = False


def _entry(state: InterviewState) -> Literal["load", "ask_design"]:
    return "ask_design" if state.get("system_design") else "load"


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    graph = StateGraph(InterviewState)
    graph.add_node("load", make_load(deps))
    graph.add_node("plan", make_plan(deps))
    graph.add_node("ask", ask)
    graph.add_node("turn", make_turn(deps))
    graph.add_node("debrief", make_debrief(deps))
    graph.add_node("save", make_save(deps))
    graph.add_node("ask_design", ask_design)
    graph.add_node("review_design", make_review_design(deps))
    graph.add_node("save_design", make_save_design(deps))
    graph.add_conditional_edges(START, _entry)
    graph.add_conditional_edges(
        "ask_design", design_submitted, {True: "review_design", False: "ask_design"}
    )
    graph.add_edge("review_design", "save_design")
    graph.add_edge("save_design", END)
    for source, target in [
        ("load", "plan"),
        ("plan", "ask"),
        ("debrief", "save"),
        ("save", END),
    ]:
        graph.add_edge(source, target)
    graph.add_conditional_edges("ask", route_ask, ["ask", "turn", "debrief"])
    graph.add_conditional_edges("turn", route_turn, ["ask", "debrief"])
    return graph
