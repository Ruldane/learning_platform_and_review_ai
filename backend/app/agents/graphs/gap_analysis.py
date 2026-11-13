"""Parcours `gap_analysis` (SPEC 5.3 étape 1, F8, D121) : l'Analyste analyse une offre ajoutée
par January, rattache ses compétences au référentiel, puis le code range l'écart et son score.

START -> load -> (analyse rangée ? match : analyze)
analyze -> (offre d'emploi ? save_analysis : reject -> END)
save_analysis -> match -> save_gap -> announce -> END

Lancé seulement par la route de la feature `postings` (`ROUTE_ONLY`), qui vérifie l'offre.
Aucun point d'arrêt ; les écritures du port sont idempotentes (SPEC 9.4)."""

from typing import Any

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.nodes.analyst import (
    announce,
    make_analyze,
    make_load,
    make_match,
    make_reject,
    make_save_analysis,
    make_save_gap,
    route_analyze,
    route_load,
)
from app.agents.nodes.analyst_steps import NOT_A_POSTING
from app.agents.runtime.deps import GraphDeps
from app.agents.state.gap_analysis import GapAnalysisState

__all__ = ["NOT_A_POSTING", "GapAnalysisInput", "build"]


class GapAnalysisInput(BaseModel):
    posting_id: str = Field(min_length=36, max_length=36)


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    graph = StateGraph(GapAnalysisState)
    graph.add_node("load", make_load(deps))
    graph.add_node("analyze", make_analyze(deps))
    graph.add_node("reject", make_reject(deps))
    graph.add_node("save_analysis", make_save_analysis(deps))
    graph.add_node("match", make_match(deps))
    graph.add_node("save_gap", make_save_gap(deps))
    graph.add_node("announce", announce)
    for source, target in [
        (START, "load"),
        ("reject", END),
        ("save_analysis", "match"),
        ("match", "save_gap"),
        ("save_gap", "announce"),
        ("announce", END),
    ]:
        graph.add_edge(source, target)
    graph.add_conditional_edges("load", route_load, ["match", "analyze"])
    graph.add_conditional_edges("analyze", route_analyze, ["save_analysis", "reject"])
    return graph
