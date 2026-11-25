"""The committee votes (SPEC F19, D147): after the debate, each persona votes — interview yes, no
or maybe — with its main objection. The four votes are independent: they go out together, each
on everything that was said. Once in the state (checkpointer), a vote is never requested again:
the finished node is not replayed after a restart. No database write. A vote that is unreadable
after the retries makes the session fail: a fallback vote would be an opinion nobody gave."""

import logging
from typing import Any

from app.agents.nodes.committee.common import (
    TURN_TIMEOUT_S,
    VOTE_REQUEST,
    Node,
    context_of,
    persona_call,
    persona_results,
)
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.hiring_committee import HiringCommitteeState
from app.agents.tools.committee_schema import (
    CommitteeContext,
    Persona,
    PersonaVote,
    Vote,
)

VOTE_WORDS = {
    "yes": "yes, I'd offer an interview",
    "no": "no, I wouldn't move forward",
    "maybe": "maybe, I'd like to know more",
}

logger = logging.getLogger(__name__)


async def _vote(
    deps: GraphDeps, ctx: CommitteeContext, spoken: list[dict[str, Any]], persona: Persona
) -> PersonaVote:
    model, messages = await persona_call(deps, ctx, persona, "vote", VOTE_REQUEST, spoken=spoken)
    found = await structured_call(
        model, Vote, messages, agent=persona, step="vote", intent="Voting"
    )
    vote = PersonaVote(persona=persona, **found.model_dump())
    text = f"I vote {VOTE_WORDS[vote.vote]}.\nMain objection: {vote.objection}"
    emit("agent.message", {"message_id": f"{persona}-vote", "text": text}, agent=persona)
    return vote


def make_votes(deps: GraphDeps) -> Node:
    @node_timeout(TURN_TIMEOUT_S)
    async def votes(state: HiringCommitteeState) -> HiringCommitteeState:
        """The four votes, in the order of the personas."""
        ctx = context_of(state)
        spoken = list(state["spoken"])
        cast = await persona_results(deps, lambda persona: _vote(deps, ctx, spoken, persona))
        logger.info("Votes cast: session %s, %d vote(s)", deps.session_id, len(cast))
        return {"votes": [vote.model_dump(mode="json") for vote in cast]}

    return votes
