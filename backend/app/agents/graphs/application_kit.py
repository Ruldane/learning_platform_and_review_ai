"""Parcours `application_kit` (SPEC 6.4, F16, D142) : le kit de candidature, sept pièces écrites en
parallèle, chacune contrôlée par le code (aucun fait que le profil ne dit pas).

START -> load -> (une branche par pièce non gardée) -> close -> END
branches : cv, letter, linkedin, followups, form_answers, pitch (Assistant de suivi), company_brief
(Éclaireur, mode `dossier`)

Les branches tournent dans le même super pas : une pièce rangée est annoncée (`artifact.ready`,
`kind = "kit_item"`) dès qu'elle est prête, sans attendre les autres. Une pièce en échec n'arrête
pas les autres. Les pièces que January a modifiées (`KitContext.keep`) ne sont jamais refaites :
aucune branche pour elles. `close` publie `run.completed` avec le compte des pièces. Lancé
seulement par la route de la feature `applications` (7.6, `ROUTE_ONLY`) ; chaque écriture d'un port
est idempotente (SPEC 9.4)."""

from typing import Any

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.nodes.scout.dossier import make_dossier
from app.agents.nodes.tracker.kit_common import close, make_load, route_pieces
from app.agents.nodes.tracker.pieces import make_cv, make_text_piece
from app.agents.runtime.deps import GraphDeps
from app.agents.state.application_kit import ApplicationKitState
from app.agents.tools.kit_schema import KIT_KINDS

__all__ = ["ApplicationKitInput", "build"]


class ApplicationKitInput(BaseModel):
    application_id: str = Field(min_length=36, max_length=36)


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    graph = StateGraph(ApplicationKitState)
    graph.add_node("load", make_load(deps))
    nodes: dict[str, Any] = {
        "cv": make_cv(deps),
        "company_brief": make_dossier(deps),
        **{
            kind: make_text_piece(deps, kind)
            for kind in ("letter", "linkedin", "followups", "form_answers", "pitch")
        },
    }
    if set(nodes) != set(KIT_KINDS):
        raise ValueError("Chaque pièce du kit doit avoir sa branche.")
    for name, node in nodes.items():
        graph.add_node(name, node)
        graph.add_edge(name, "close")
    graph.add_node("close", close)
    graph.add_edge(START, "load")
    graph.add_conditional_edges("load", route_pieces, [*KIT_KINDS, "close"])
    graph.add_edge("close", END)
    return graph
