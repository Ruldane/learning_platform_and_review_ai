"""La fin de l'évaluation d'un projet (P3, D165) : `save` range l'issue par le port (idempotent par
session : un nœud rejoué ne range rien de plus), `announce` annonce le projet (`artifact.ready`,
`kind = "project"`) et dit le résultat en une phrase de nombres comptés par le code.

Journaux : identifiants, nombres et codes, jamais un texte du projet (17.2)."""

import logging

from app.agents.nodes.practitioner.outcome import from_state, summary_text
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.state.project_review import Node, ProjectReviewState

__all__ = ["announce", "make_save"]

AGENT = "practitioner"

logger = logging.getLogger(__name__)


def make_save(deps: GraphDeps) -> Node:
    @node_timeout()
    async def save(state: ProjectReviewState) -> ProjectReviewState:
        outcome = from_state(state["outcome"])
        await deps.ports.projects.save_review(
            deps.user_id, deps.session_id, state["project_id"], outcome
        )
        drafts = outcome.drafts or []
        logger.info(
            "Évaluation rangée : session %s, projet %s, verdict %s, %d critère(s) atteint(s), "
            "%d brouillon(s) dont %d à vérifier",
            deps.session_id,
            state["project_id"],
            outcome.verdict,
            sum(result.met for result in outcome.results),
            len(drafts),
            sum(draft.status == "to_check" for draft in drafts),
        )
        return {}

    return save


def announce(state: ProjectReviewState) -> ProjectReviewState:
    project_id = state["project_id"]
    emit(
        "artifact.ready",
        {
            "artifact_id": project_id,
            "kind": "project",
            "title": state["title"],
            "url": f"/competences/portfolio/{project_id}",
        },
        agent=AGENT,
    )
    return {"summary": summary_text(from_state(state["outcome"]))}
