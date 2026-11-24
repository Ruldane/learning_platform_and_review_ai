"""Parcours `daily_brief` (P11, D161) : les deux rubriques du brief du matin qui passent par un
modèle. Le bloc, les révisions, les relances, les offres et l'avancement sont calculés par le code
(feature `brief`) ; ici, la ressource (l'Éclaireur choisit parmi huit résultats d'une recherche du
mois, le code lit la page) et le conseil (deux phrases du Modérateur, nombres contrôlés par le
code) : deux appels rapides au plus.

START -> load -> resource -> advice -> close -> END

Chaque rubrique relit l'état du brief par le port (`context`) et se saute si elle est déjà rangée :
un redémarrage avant le conseil ne rappelle pas l'Éclaireur. Une rubrique en panne se range vide
(`None`), jamais en erreur : elle n'empêche ni l'autre ni la fin du parcours. Aucune interruption,
aucune boucle. Lancé seulement par la feature `brief` (8.6, `ROUTE_ONLY`)."""

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.nodes.moderator_brief import make_advice
from app.agents.nodes.scout.brief_resource import make_resource
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.state.daily_brief import DailyBriefState, Node

__all__ = ["SUMMARY", "DailyBriefInput", "build"]

SUMMARY = "Your daily brief is ready."

logger = logging.getLogger(__name__)


class DailyBriefInput(BaseModel):
    brief_id: str = Field(min_length=36, max_length=36)


def make_load(deps: GraphDeps) -> Node:
    @node_timeout()
    async def load(state: DailyBriefState) -> DailyBriefState:
        ctx = await deps.ports.brief.context(deps.user_id, state["brief_id"])
        logger.info(
            "Brief lu : session %s, brief %s, ressource rangée %s, conseil rangé %s",
            deps.session_id,
            ctx.brief_id,
            ctx.resource_done,
            ctx.advice_done,
        )
        return {}

    return load


def make_close(deps: GraphDeps) -> Node:
    @node_timeout()
    async def close(state: DailyBriefState) -> DailyBriefState:
        logger.info("Brief prêt : session %s, brief %s", deps.session_id, state["brief_id"])
        return {"summary": SUMMARY}

    return close


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    graph = StateGraph(DailyBriefState)
    graph.add_node("load", make_load(deps))
    graph.add_node("resource", make_resource(deps))
    graph.add_node("advice", make_advice(deps))
    graph.add_node("close", make_close(deps))
    graph.add_edge(START, "load")
    graph.add_edge("load", "resource")
    graph.add_edge("resource", "advice")
    graph.add_edge("advice", "close")
    graph.add_edge("close", END)
    return graph
