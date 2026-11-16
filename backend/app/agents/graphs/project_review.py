"""Parcours `project_review` (P2 à P4, D165) : le Praticien évalue le rendu d'un mini projet contre
les critères de l'énoncé ; le code décide du verdict ; validé, il écrit les quatre brouillons de
January, que le code contrôle (`text_claims`).

START -> load -> read_repo -> (rien à lire ? skip : evaluate)
skip -> save ; evaluate -> (validé ? drafts : save) ; drafts -> save -> announce -> END

Sans description ni dépôt lisible, aucun appel au modèle : « à reprendre », jamais « validé » sur
rien. Aucune interruption, aucune boucle ; chaque nœud relit les entrées par le port et l'écriture
du port est idempotente par session (SPEC 9.4). Trois appels standard au plus (évaluation,
brouillons, un nouvel essai des brouillons). Lancé seulement par la feature `projects` (8.10,
`ROUTE_ONLY`)."""

from typing import Any

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.nodes.practitioner.drafts import make_drafts
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


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    graph = StateGraph(ProjectReviewState)
    graph.add_node("load", make_load(deps))
    graph.add_node("read_repo", make_read_repo(deps))
    graph.add_node("skip", make_skip(deps))
    graph.add_node("evaluate", make_evaluate(deps))
    graph.add_node("drafts", make_drafts(deps))
    graph.add_node("save", make_save(deps))
    graph.add_node("announce", announce)
    for source, target in [
        (START, "load"),
        ("load", "read_repo"),
        ("skip", "save"),
        ("drafts", "save"),
        ("save", "announce"),
        ("announce", END),
    ]:
        graph.add_edge(source, target)
    graph.add_conditional_edges("read_repo", route_read, ["skip", "evaluate"])
    graph.add_conditional_edges("evaluate", route_evaluate, ["drafts", "save"])
    return graph
