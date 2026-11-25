"""Reading and filing of the hiring committee (SPEC F19, D147): `load` reads the context through
the port (read-only), `save` files the outcome — the four votes, the verdict, the objections and
the three changes — through the port, **idempotent per session** (SPEC 9.4): the only node that
writes. A node replayed after a stop rereads its session's outcome and files nothing a second
time.

Logs: identifiers and numbers only, never the CV, the posting, a speech or the company
(17.2)."""

import logging

from app.agents.nodes.committee.common import Node
from app.agents.nodes.committee.synthesis import AGENT
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.state.hiring_committee import HiringCommitteeState
from app.agents.tools.committee_schema import PersonaVote, Synthesis

logger = logging.getLogger(__name__)


def make_load(deps: GraphDeps) -> Node:
    @node_timeout()
    async def load(state: HiringCommitteeState) -> HiringCommitteeState:
        ctx = await deps.ports.committee.context(deps.user_id, state["run_id"])
        logger.info(
            "Committee read: session %s, run %s, size %s",
            deps.session_id,
            state["run_id"],
            ctx.size,
        )
        return {"context": ctx.model_dump(mode="json")}

    return load


def make_save(deps: GraphDeps) -> Node:
    @node_timeout()
    async def save(state: HiringCommitteeState) -> HiringCommitteeState:
        """The committee's outcome, the only write; replayed, the port rereads the session's."""
        votes = [PersonaVote.model_validate(v) for v in state["votes"]]
        synthesis = Synthesis.model_validate(state["synthesis"])
        await deps.ports.committee.save_result(
            deps.user_id, deps.session_id, state["run_id"], votes, synthesis
        )
        logger.info(
            "Committee filed: session %s, run %s, verdict %s",
            deps.session_id,
            state["run_id"],
            synthesis.verdict,
        )
        text = (
            f"The simulated hiring committee voted {synthesis.verdict} and proposed "
            f"{len(synthesis.changes)} changes."
        )
        emit("agent.message", {"message_id": f"{AGENT}-fin", "text": text}, agent=AGENT)
        return {"summary": text}

    return save
