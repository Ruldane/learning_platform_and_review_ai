"""Parcours `interview` (SPEC F10, 9.4, D145) : un entretien blanc écrit, mené par l'Intervieweur.

START -> load -> plan -> ask
ask -> (réponse illisible : ask) | (réponse : turn) | (« Terminer l'entretien » : debrief)
turn -> (relance ou question suivante : ask) | (plus de question : debrief)
debrief -> save -> END

`ask` pose la question par `interrupt()` (seul dans son nœud, SPEC 9.4) ; le plan, la question en
cours et les échanges vivent dans l'état (checkpointer) : un redémarrage pendant l'attente repose
la même question sans rien redemander au modèle. Une relance au plus par question. « Terminer »
après au moins une réponse : débrief sur les questions répondues ; avant toute réponse : `save`
range un entretien arrêté, sans débrief. `save` est la seule écriture, idempotente par session.
Lancé seulement par la route de la feature `applications` (7.9, `ROUTE_ONLY`)."""

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
