"""Parcours `learning_council` (SPEC 3.1, D84) : le Conseil d'apprentissage.

Première moitié (tâche 4.3) : le Modérateur lit l'objectif et la mémoire, prépare le cadrage et
s'arrête (point d'arrêt n° 1) ; l'Éclaireur cherche, lit, note, garde en mémoire et repère des
praticiens. Ses nœuds entrent tels quels, nœud pour nœud (pas de sous-graphe) : rejeu et points
de contrôle identiques à `web_research`. La tâche 4.4 remplace END par le débat.

START -> context -> frame -> ask_framing -> apply_framing -> plan -> search -> read -> judge
      -> remember -> spot_people -> END
"""

from typing import Any

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.nodes.moderator import ask_framing, make_apply_framing, make_context, make_frame
from app.agents.nodes.scout import make_judge, make_plan, make_read, make_remember, make_search
from app.agents.nodes.scout.people import make_spot_people
from app.agents.runtime.deps import GraphDeps
from app.agents.state.learning_council import CouncilState


class LearningCouncilInput(BaseModel):
    goal_id: str = Field(min_length=36, max_length=36)


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    graph = StateGraph(CouncilState)
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
    order = [
        START,
        "context",
        "frame",
        "ask_framing",
        "apply_framing",
        "plan",
        "search",
        "read",
        "judge",
        "remember",
        "spot_people",
        END,
    ]
    for source, target in zip(order, order[1:], strict=False):
        graph.add_edge(source, target)
    return graph
