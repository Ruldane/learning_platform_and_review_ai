"""The committee's first impressions (SPEC F19, D147): each persona reads the CV and the posting,
and only those, then gives its impression in 150 words at most (cut by the code, `speak`). The
four calls are independent: they go out together. The node writes nothing to the database; it
puts the speeches in the state (checkpointer), a finished node is never redone."""

import logging
from typing import Any

from app.agents.nodes.committee.common import (
    IMPRESSION_REQUEST,
    TURN_TIMEOUT_S,
    Node,
    context_of,
    persona_call,
    persona_results,
)
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.speech import speak
from app.agents.state.hiring_committee import HiringCommitteeState
from app.agents.tools.committee_schema import MAX_WORDS, CommitteeContext, Persona

logger = logging.getLogger(__name__)


async def _impression(deps: GraphDeps, ctx: CommitteeContext, persona: Persona) -> dict[str, Any]:
    model, messages = await persona_call(deps, ctx, persona, "impression", IMPRESSION_REQUEST)
    spoken = await speak(
        model,
        messages,
        agent=persona,
        step="impression",
        intent="giving my first impression",
        catalog=[],
        max_words=MAX_WORDS,
    )
    return {"persona": persona, "round": 0, "text": spoken.text}


def make_impressions(deps: GraphDeps) -> Node:
    @node_timeout(TURN_TIMEOUT_S)
    async def impressions(state: HiringCommitteeState) -> HiringCommitteeState:
        """Four impressions, in the order of the personas."""
        ctx = context_of(state)
        spoken = await persona_results(deps, lambda persona: _impression(deps, ctx, persona))
        logger.info("Impressions given: session %s, %d persona(s)", deps.session_id, len(spoken))
        return {"spoken": spoken}

    return impressions
