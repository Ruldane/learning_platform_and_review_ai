"""Parcours `application_intake` (SPEC 6.1, 6.3, F5, D141) : « j'ai postulé hier chez X pour le
poste Y » devient une fiche de candidature, confirmée par January avant d'être créée.

START -> load -> parse -> alerts -> ask
ask -> (réponse invalide : ask) | (create, distinct : save) | (cancel, open : leave)
save -> announce -> END ; leave -> END

`ask` pose la question « Je crée cette fiche ? » par `interrupt()` (seul dans son nœud, SPEC 9.4)
avec l'alerte de doublon s'il y en a une ; `save` crée la fiche par le port, idempotent par
session. Lancé seulement par la route de la feature `applications` (`ROUTE_ONLY`), qui vérifie
qu'aucune autre session d'intake n'est ouverte."""

from typing import Any

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.nodes.tracker import (
    announce,
    ask_confirm,
    leave,
    make_alerts,
    make_load,
    make_parse,
    make_save,
    route_confirm,
)
from app.agents.runtime.deps import GraphDeps
from app.agents.state.application_intake import ApplicationIntakeState

__all__ = ["ApplicationIntakeInput", "build"]

TEXT_MAX = 1000


class ApplicationIntakeInput(BaseModel):
    text: str = Field(min_length=1, max_length=TEXT_MAX)


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    graph = StateGraph(ApplicationIntakeState)
    graph.add_node("load", make_load(deps))
    graph.add_node("parse", make_parse(deps))
    graph.add_node("alerts", make_alerts(deps))
    graph.add_node("ask", ask_confirm)
    graph.add_node("save", make_save(deps))
    graph.add_node("announce", announce)
    graph.add_node("leave", leave)
    for source, target in [
        (START, "load"),
        ("load", "parse"),
        ("parse", "alerts"),
        ("alerts", "ask"),
        ("save", "announce"),
        ("announce", END),
        ("leave", END),
    ]:
        graph.add_edge(source, target)
    graph.add_conditional_edges("ask", route_confirm, ["ask", "save", "leave"])
    return graph
