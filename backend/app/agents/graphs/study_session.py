"""Parcours `study_session` (SPEC F14, 9.2, D102) : le Tuteur mène une séance d'étude guidée sur
la leçon d'un module.

START -> context -> open -> (position) ; advance -> (position)
position : section ou exercice ou question finale -> teach ; finale non écrite -> final_intro
           -> teach ; tout est réglé -> ask_finish
teach -> ask -> route_answer
route_answer : réponse -> check -> advance ; « Je bloque » -> hint -> ask (3 fois au plus),
               puis reveal -> advance ; « Passer » -> skip -> advance ;
               « Terminer » -> summarize ; réponse illisible -> ask (même question)
ask_finish -> summarize (toute autre réponse : ask_finish) ; summarize -> wrap_up -> END

Deux points d'arrêt (`ask`, `ask_finish`), chacun seul dans son nœud (SPEC 9.4). Une seule
écriture, `wrap_up` (port, idempotent)."""

from typing import Any

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.nodes.tutor import (
    advance,
    ask,
    ask_finish,
    make_check,
    make_context,
    make_final_intro,
    make_hint,
    make_open,
    make_summarize,
    make_teach,
    make_wrap_up,
    reveal,
    route_answer,
    route_finish,
    route_position,
    skip,
)
from app.agents.runtime.deps import GraphDeps
from app.agents.state.study_session import StudySessionState

POSITIONS = ["teach", "final_intro", "ask_finish"]


class StudySessionInput(BaseModel):
    study_session_id: str = Field(min_length=36, max_length=36)


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    graph = StateGraph(StudySessionState)
    graph.add_node("context", make_context(deps))
    graph.add_node("open", make_open(deps))
    graph.add_node("teach", make_teach(deps))
    graph.add_node("final_intro", make_final_intro(deps))
    graph.add_node("ask", ask)
    graph.add_node("check", make_check(deps))
    graph.add_node("hint", make_hint(deps))
    graph.add_node("reveal", reveal)
    graph.add_node("skip", skip)
    graph.add_node("advance", advance)
    graph.add_node("ask_finish", ask_finish)
    graph.add_node("summarize", make_summarize(deps))
    graph.add_node("wrap_up", make_wrap_up(deps))
    for source, target in [
        (START, "context"),
        ("context", "open"),
        ("final_intro", "teach"),
        ("teach", "ask"),
        ("check", "advance"),
        ("hint", "ask"),
        ("reveal", "advance"),
        ("skip", "advance"),
        ("summarize", "wrap_up"),
        ("wrap_up", END),
    ]:
        graph.add_edge(source, target)
    graph.add_conditional_edges("open", route_position, POSITIONS)
    graph.add_conditional_edges("advance", route_position, POSITIONS)
    graph.add_conditional_edges(
        "ask", route_answer, ["ask", "check", "hint", "reveal", "skip", "summarize"]
    )
    graph.add_conditional_edges("ask_finish", route_finish, ["ask_finish", "summarize"])
    return graph
