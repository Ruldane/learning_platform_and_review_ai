"""Parcours `project_review` (P2 à P4, D165) : le Praticien évalue le rendu d'un mini projet contre
les critères de l'énoncé ; le code décide du verdict ; validé, il écrit les quatre brouillons de
January, que le code contrôle (`text_claims`).

START -> load -> read_repo -> (rien à lire ? skip : evaluate)
skip -> save ; evaluate -> (validé ? drafts : save) ; drafts -> (à corriger ? redo : save)
redo -> save -> announce -> END

Mode `drafts` (D173 n° 4, D181) : un projet **déjà validé** sans ses brouillons (leur écriture
avait échoué) : `load -> seed -> drafts -> (à corriger ? redo : save)`, sans lecture du dépôt ni
évaluation ; `save` ne range que les brouillons (`save_drafts`). Mêmes plafonds : un appel
standard et un nouvel essai au plus.

Sans description ni dépôt lisible, aucun appel au modèle : « à reprendre », jamais « validé » sur
rien. Aucune interruption, aucune boucle ; chaque nœud relit les entrées par le port et l'écriture
du port est idempotente par session (SPEC 9.4). Trois appels standard au plus (évaluation,
brouillons, un nouvel essai des brouillons dans son propre nœud et son propre délai : sa panne
garde le premier jet « à vérifier »). Lancé seulement par la feature `projects` (8.10,
`ROUTE_ONLY`)."""

from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.nodes.practitioner.drafts import make_drafts, make_redo, route_drafts
from app.agents.nodes.practitioner.drafts_only import make_seed, route_load
from app.agents.nodes.practitioner.evaluate import (
    NO_REPO_FEEDBACK,
    make_evaluate,
    make_load,
    make_read_repo,
    make_skip,
    route_evaluate,
    route_read,
)
from app.agents.nodes.practitioner.finish import announce, make_save
from app.agents.runtime.deps import GraphDeps
from app.agents.state.project_review import ProjectReviewState

__all__ = ["NO_REPO_FEEDBACK", "ProjectReviewInput", "build"]


class ProjectReviewInput(BaseModel):
    project_id: str = Field(min_length=36, max_length=36)
    mode: Literal["review", "drafts"] = "review"


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    graph = StateGraph(ProjectReviewState)
    graph.add_node("load", make_load(deps))
    graph.add_node("read_repo", make_read_repo(deps))
    graph.add_node("seed", make_seed(deps))
    graph.add_node("skip", make_skip(deps))
    graph.add_node("evaluate", make_evaluate(deps))
    graph.add_node("drafts", make_drafts(deps))
    graph.add_node("redo", make_redo(deps))
    graph.add_node("save", make_save(deps))
    graph.add_node("announce", announce)
    for source, target in [
        (START, "load"),
        ("seed", "drafts"),
        ("skip", "save"),
        ("redo", "save"),
        ("save", "announce"),
        ("announce", END),
    ]:
        graph.add_edge(source, target)
    graph.add_conditional_edges("load", route_load, ["read_repo", "seed"])
    graph.add_conditional_edges("read_repo", route_read, ["skip", "evaluate"])
    graph.add_conditional_edges("evaluate", route_evaluate, ["drafts", "save"])
    graph.add_conditional_edges("drafts", route_drafts, ["redo", "save"])
    return graph
