"""The Strategist proposes 2 to 3 paths (SPEC 3.1, step 5, D85), per batch: a new round of
debate requested at the time of the choice gives a new batch. It starts from the Scribe's minutes
(agent output, wrapped), January's messages, the goal and the framing.

Replayed after a stop, the node first rereads the batch already recorded (`saved_proposals`) and
re-emits it as is, names and details together, without calling the model again (D85); the write
stays idempotent per `(session, batch)`, never a second batch."""

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agents.nodes.council_rules import Node, goal_vars, notes_prompt
from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.learning_council import CouncilState
from app.agents.tools.council_port import ProposalDraft, SavedProposal

AGENT = "strategist"
MIN_PROPOSALS = 2
MAX_PROPOSALS = 3


class ProposalSet(BaseModel):
    proposals: list[ProposalDraft] = Field(min_length=MIN_PROPOSALS, max_length=MAX_PROPOSALS)


def _prompt(state: CouncilState) -> str:
    minutes = state.get("minutes") or "No minutes."
    return render_prompt(
        AGENT,
        mode="propose",
        **goal_vars(state),
        minutes=untrusted(minutes, "Scribe's minutes"),
        notes=notes_prompt(state.get("notes", [])),
        min_proposals=MIN_PROPOSALS,
        max_proposals=MAX_PROPOSALS,
    )


def _entry(saved: SavedProposal) -> dict[str, Any]:
    ref = saved.ref
    return {
        **saved.draft.model_dump(),
        "proposal_id": ref.proposal_id,
        "rank": ref.rank,
        "name": ref.name,
    }


async def _draft(deps: GraphDeps, state: CouncilState, batch: int) -> list[SavedProposal]:
    """New batch: the Strategist writes, the port records (ids, ranks, names)."""
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    found = await structured_call(
        model,
        ProposalSet,
        [SystemMessage(_prompt(state)), HumanMessage("Propose the paths.")],
        agent=AGENT,
        step=f"propositions-{batch}",
        intent="suggesting learning paths",
    )
    refs = await deps.ports.council.save_proposals(
        deps.user_id, deps.session_id, state["goal_id"], batch=batch, proposals=found.proposals
    )
    by_rank = dict(enumerate(found.proposals, start=1))
    return [SavedProposal(ref, by_rank[ref.rank]) for ref in refs if ref.rank in by_rank]


def make_propose(deps: GraphDeps) -> Node:
    @node_timeout()
    async def propose(state: CouncilState) -> CouncilState:
        batch = state.get("batch", 0) + 1
        council = deps.ports.council
        saved = await council.saved_proposals(deps.user_id, deps.session_id, batch=batch)
        if not saved:
            saved = await _draft(deps, state, batch)
        for item in saved:
            emit(
                "proposal.ready",
                {"proposal_id": item.ref.proposal_id, "title": item.ref.name},
                agent=AGENT,
            )
        return {"batch": batch, "proposals": [_entry(item) for item in saved], "choice": None}

    return propose
