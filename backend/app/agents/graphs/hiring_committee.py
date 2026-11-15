"""Parcours `hiring_committee` (SPEC F19, 9.3, D147) : le comité de recrutement simulé. Quatre
personas lisent le CV d'une version prête face à l'offre, donnent leur première impression,
débattent deux tours, votent ; le Modérateur classe les objections et propose trois changements.

START -> load -> impressions -> round_1 -> round_2 -> votes -> synthesis -> save -> END

17 appels au plus : 4 impressions, 4 prises de parole au tour 1, 4 au tour 2, 4 votes, 1 synthèse.
Ce que le code décide : l'ordre de parole (rotation fixe), le verdict (majorité des votes ; égalité
ou aucune majorité : « peut-être ») et les termes « à acquérir » des changements. Aucun
`interrupt()` (January regarde le comité débattre). `save` est la seule écriture, idempotente par
session (SPEC 9.4) ; `durability="sync"` (D46) ne rejoue jamais un nœud terminé, donc jamais un
vote donné.
Lancé seulement par la route de la feature `applications` (7.10, `ROUTE_ONLY`)."""

from typing import Any

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.nodes.committee import (
    make_impressions,
    make_load,
    make_round,
    make_save,
    make_synthesis,
    make_votes,
)
from app.agents.runtime.deps import GraphDeps
from app.agents.state.hiring_committee import HiringCommitteeState

__all__ = ["HiringCommitteeInput", "build"]


class HiringCommitteeInput(BaseModel):
    run_id: str = Field(min_length=36, max_length=36)


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    graph = StateGraph(HiringCommitteeState)
    nodes: dict[str, Any] = {
        "load": make_load(deps),
        "impressions": make_impressions(deps),
        "round_1": make_round(deps, 1),
        "round_2": make_round(deps, 2),
        "votes": make_votes(deps),
        "synthesis": make_synthesis(deps),
        "save": make_save(deps),
    }
    for name, node in nodes.items():
        graph.add_node(name, node)
    chain = [START, *nodes, END]
    for source, target in zip(chain, chain[1:], strict=False):
        graph.add_edge(source, target)
    return graph
