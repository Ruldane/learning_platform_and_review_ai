"""Parcours `market_radar` (P5, P6, D159) : le relevé du marché de l'emploi. L'Éclaireur cherche
les offres du mois et les lit par passages de dix liens, l'Analyste en extrait compétences, outils,
niveau et salaire par lots de cinq ; le classement, l'évolution et les alertes sont calculés par le
code, ailleurs (feature `radar`).

START -> load -> search -> read (boucle) -> extract (boucle) -> finish -> END

Deux boucles par arête conditionnelle (aucun nœud d'aiguillage : chaque passage est un pas du
graphe). Chacune relit l'état du relevé par le port à chaque passage ; un redémarrage ne relit
et ne réextrait rien. Au pire : 6 passages de lecture (60 lectures) et 10 d'extraction (50 offres),
soit 19 pas. `recursion_limit` (pas de LangGraph, documentation actuelle : 10 007 par défaut depuis
la 1.1.4, et non 25) n'est donc jamais atteint ; le lancement (8.4) le fixe tout de même à
6 + 2 × (60 / 10 + 50 / 5) = 38 pour qu'une boucle sans fin échoue vite. Aucune interruption.
Lancé seulement par la route de la feature `radar` (8.4, `ROUTE_ONLY`)."""

from typing import Any

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.nodes.analyst_radar import make_extract, route_extract
from app.agents.nodes.scout.radar import (
    make_finish,
    make_load,
    make_read,
    make_search,
    route_read,
)
from app.agents.runtime.deps import GraphDeps
from app.agents.state.market_radar import MarketRadarState

__all__ = ["MarketRadarInput", "build"]


class MarketRadarInput(BaseModel):
    run_id: str = Field(min_length=36, max_length=36)


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    graph = StateGraph(MarketRadarState)
    graph.add_node("load", make_load(deps))
    graph.add_node("search", make_search(deps))
    graph.add_node("read", make_read(deps))
    graph.add_node("extract", make_extract(deps))
    graph.add_node("finish", make_finish(deps))
    graph.add_edge(START, "load")
    graph.add_edge("load", "search")
    graph.add_edge("search", "read")
    graph.add_conditional_edges("read", route_read, ["read", "extract"])
    graph.add_conditional_edges("extract", route_extract, ["extract", "finish"])
    graph.add_edge("finish", END)
    return graph
