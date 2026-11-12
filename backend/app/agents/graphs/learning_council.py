"""Parcours `learning_council` (SPEC 3.1, D84, D85) : le Conseil d'apprentissage.

Cadrage par le Modérateur (point d'arrêt n° 1), recherche et praticiens de l'Éclaireur (ses
nœuds tels quels, nœud pour nœud : rejeu et points de contrôle identiques à `web_research`),
puis débat, tableau du Scribe, propositions du Stratège et choix de January (point d'arrêt n° 2).

START -> context -> frame -> ask_framing -> apply_framing -> plan -> search -> read -> judge
      -> remember -> spot_people -> round_start -> turn ⟲ -> round_end
round_start : `to_proposals` lu avant un tour ≥ 2 -> prerequisites
round_end : tour 1 -> domain_map -> (suite) ; arrêt ou dernier tour -> prerequisites
            sinon -> round_start
prerequisites -> minutes -> propose -> proposal_boards -> ask_choice -> route_choice
route_choice : another_round -> round_start ; choix invalide -> ask_choice ; choisi -> finalize
finalize -> END
"""

from typing import Any

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.nodes.council_choice import ask_choice, make_finalize, route_choice
from app.agents.nodes.council_rules import debate_over
from app.agents.nodes.debate_turn import make_turn
from app.agents.nodes.moderator import (
    ask_framing,
    make_apply_framing,
    make_context,
    make_frame,
    make_round_end,
    make_round_start,
)
from app.agents.nodes.scout import make_judge, make_plan, make_read, make_remember, make_search
from app.agents.nodes.scout.people import make_spot_people
from app.agents.nodes.scribe import (
    make_domain_map,
    make_minutes,
    make_prerequisites,
    make_proposal_boards,
)
from app.agents.nodes.strategist import make_propose
from app.agents.runtime.deps import GraphDeps
from app.agents.state.learning_council import CouncilState


class LearningCouncilInput(BaseModel):
    goal_id: str = Field(min_length=36, max_length=36)


def _turns_left(state: CouncilState) -> bool:
    return state.get("turn_index", 0) < len(state.get("order", []))


def after_round_start(state: CouncilState) -> str:
    return "turn" if _turns_left(state) else "prerequisites"


def after_turn(state: CouncilState) -> str:
    return "turn" if _turns_left(state) else "round_end"


def after_round_end(state: CouncilState) -> str:
    if state.get("round", 1) == 1:
        return "domain_map"
    return "prerequisites" if debate_over(state) else "round_start"


def after_domain_map(state: CouncilState) -> str:
    return "prerequisites" if debate_over(state) else "round_start"


def _research(graph: StateGraph[Any, Any, Any, Any], deps: GraphDeps) -> None:
    graph.add_node("context", make_context(deps))
    graph.add_node("frame", make_frame(deps))
    graph.add_node("ask_framing", ask_framing)
    graph.add_node("apply_framing", make_apply_framing(deps))
    graph.add_node("plan", make_plan(deps))
    graph.add_node("search", make_search(deps))
    graph.add_node("read", make_read(deps))
    graph.add_node("judge", make_judge(deps))
    graph.add_node("remember", make_remember(deps))
    graph.add_node("spot_people", make_spot_people(deps))
    order = [START, "context", "frame", "ask_framing", "apply_framing", "plan", "search"]
    order += ["read", "judge", "remember", "spot_people", "round_start"]
    for source, target in zip(order, order[1:], strict=False):
        graph.add_edge(source, target)


def _debate(graph: StateGraph[Any, Any, Any, Any], deps: GraphDeps) -> None:
    graph.add_node("round_start", make_round_start(deps))
    graph.add_node("turn", make_turn(deps))
    graph.add_node("round_end", make_round_end(deps))
    graph.add_node("domain_map", make_domain_map(deps))
    graph.add_conditional_edges("round_start", after_round_start, ["turn", "prerequisites"])
    graph.add_conditional_edges("turn", after_turn, ["turn", "round_end"])
    graph.add_conditional_edges(
        "round_end", after_round_end, ["domain_map", "prerequisites", "round_start"]
    )
    graph.add_conditional_edges("domain_map", after_domain_map, ["prerequisites", "round_start"])


def _proposals(graph: StateGraph[Any, Any, Any, Any], deps: GraphDeps) -> None:
    graph.add_node("prerequisites", make_prerequisites(deps))
    graph.add_node("minutes", make_minutes(deps))
    graph.add_node("propose", make_propose(deps))
    graph.add_node("proposal_boards", make_proposal_boards(deps))
    graph.add_node("ask_choice", ask_choice)
    graph.add_node("finalize", make_finalize(deps))
    for source, target in [
        ("prerequisites", "minutes"),
        ("minutes", "propose"),
        ("propose", "proposal_boards"),
        ("proposal_boards", "ask_choice"),
        ("finalize", END),
    ]:
        graph.add_edge(source, target)
    graph.add_conditional_edges(
        "ask_choice", route_choice, ["ask_choice", "round_start", "finalize"]
    )


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    graph = StateGraph(CouncilState)
    _research(graph, deps)
    _debate(graph, deps)
    _proposals(graph, deps)
    return graph
