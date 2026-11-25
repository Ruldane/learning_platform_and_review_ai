"""The end of a project evaluation (P3, D165): `save` files the outcome through the port
(idempotent per session: a replayed node files nothing more), `announce` announces the project
(`artifact.ready`, `kind = "project"`) and states the result in one sentence of figures counted
by the code.

Logs: identifiers, numbers and codes, never a project text (17.2)."""

import logging

from app.agents.nodes.practitioner.outcome import from_state, summary_text
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.state.project_review import Node, ProjectReviewState

__all__ = ["announce", "make_save"]

AGENT = "practitioner"
NOT_SAVED = "The project is approved. Its drafts are available."

logger = logging.getLogger(__name__)


def make_save(deps: GraphDeps) -> Node:
    @node_timeout()
    async def save(state: ProjectReviewState) -> ProjectReviewState:
        outcome = from_state(state["outcome"])
        if state.get("mode") == "drafts":  # an already validated project: only its drafts
            drafts = outcome.drafts or []
            saved = await deps.ports.projects.save_drafts(
                deps.user_id, deps.session_id, state["project_id"], drafts
            )
            logger.info(
                "Drafts %s: session %s, project %s, %d draft(s) of which %d to verify",
                "stored" if saved else "not stored",
                deps.session_id,
                state["project_id"],
                len(drafts),
                sum(draft.status == "to_check" for draft in drafts),
            )
            return {"drafts_saved": saved}
        await deps.ports.projects.save_review(
            deps.user_id, deps.session_id, state["project_id"], outcome
        )
        drafts = outcome.drafts or []
        logger.info(
            "Evaluation stored: session %s, project %s, verdict %s, %d criteria met, "
            "%d draft(s) of which %d to verify",
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
            "url": f"/skills/portfolio/{project_id}",
        },
        agent=AGENT,
    )
    outcome = from_state(state["outcome"])
    if state.get("mode") == "drafts" and outcome.drafts and state.get("drafts_saved") is False:
        return {"summary": NOT_SAVED}  # the port ignored the write: nothing new is ready
    return {"summary": summary_text(outcome)}
