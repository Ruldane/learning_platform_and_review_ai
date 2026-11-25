"""Rerun only the drafts of an already validated project (`drafts` mode of `project_review`,
D173 no. 4, D181): the evaluation was stored "validated" but writing the drafts had failed
("drafts unavailable"). `route_load` skips reading the repository and the evaluation; `seed`
puts in the state a "validated" outcome with no result and no draft, which the `drafts` and
`redo` nodes complete as after an evaluation; `save` then only stores the drafts
(`save_drafts`). No evaluation is redone: nothing of the verdict is reread or rewritten.

Logs: identifiers only."""

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
        """The starting outcome of the drafts: validated, with no result (the verdict stays the one
        already stored), with no draft."""
        logger.info("Drafts only: session %s, project %s", deps.session_id, state["project_id"])
        outcome = ReviewOutcome(
            verdict="validated", results=[], feedback="", repo_status="none", drafts=None
        )
        return {"outcome": to_state(outcome)}

    return seed
