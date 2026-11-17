"""Relancer seulement les brouillons d'un projet déjà validé (mode `drafts` de `project_review`,
D173 n° 4, D181) : l'évaluation a été rangée « validée » mais l'écriture des brouillons avait
échoué (« brouillons indisponibles »). `route_load` saute la lecture du dépôt et l'évaluation ;
`seed` pose dans l'état une issue « validée » sans résultat ni brouillon, que les nœuds `drafts`
et `redo` complètent comme après une évaluation ; `save` ne range alors que les brouillons
(`save_drafts`). Aucune évaluation n'est refaite : rien du verdict n'est relu ni réécrit.

Journaux : identifiants seulement."""

import logging

from app.agents.nodes.practitioner.outcome import to_state
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.state.project_review import Node, ProjectReviewState
from app.agents.tools.project_port import ReviewOutcome

__all__ = ["make_seed", "route_load"]

logger = logging.getLogger(__name__)


def route_load(state: ProjectReviewState) -> str:
    return "seed" if state.get("mode") == "drafts" else "read_repo"


def make_seed(deps: GraphDeps) -> Node:
    @node_timeout()
    async def seed(state: ProjectReviewState) -> ProjectReviewState:
        """L'issue de départ des brouillons : validée, sans résultat (le verdict reste celui qui
        est déjà rangé), sans brouillon."""
        logger.info(
            "Brouillons seuls : session %s, projet %s", deps.session_id, state["project_id"]
        )
        outcome = ReviewOutcome(
            verdict="validated", results=[], feedback="", repo_status="none", drafts=None
        )
        return {"outcome": to_state(outcome)}

    return seed
