"""Les premières impressions du comité (SPEC F19, D147) : chaque persona lit le CV et l'offre, et
elles seulement, puis donne son impression en 150 mots au plus (coupe du code, `speak`). Les
quatre appels sont indépendants : ils partent ensemble. Le nœud n'écrit rien en base ; il pose les
paroles dans l'état (checkpointer), un nœud terminé n'est jamais refait."""

import logging
from typing import Any

from app.agents.nodes.committee.common import (
    IMPRESSION_REQUEST,
    TURN_TIMEOUT_S,
    Node,
    context_of,
    persona_call,
    together,
)
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.speech import speak
from app.agents.state.hiring_committee import HiringCommitteeState
from app.agents.tools.committee_schema import MAX_WORDS, PERSONAS, CommitteeContext, Persona

logger = logging.getLogger(__name__)


async def _impression(deps: GraphDeps, ctx: CommitteeContext, persona: Persona) -> dict[str, Any]:
    model, messages = await persona_call(deps, ctx, persona, "impression", IMPRESSION_REQUEST)
    spoken = await speak(
        model,
        messages,
        agent=persona,
        step="impression",
        intent="je donne ma première impression",
        catalog=[],
        max_words=MAX_WORDS,
    )
    return {"persona": persona, "round": 0, "text": spoken.text}


def make_impressions(deps: GraphDeps) -> Node:
    @node_timeout(TURN_TIMEOUT_S)
    async def impressions(state: HiringCommitteeState) -> HiringCommitteeState:
        """Quatre impressions, dans l'ordre des personas."""
        ctx = context_of(state)
        spoken = await together(*(_impression(deps, ctx, p) for p in PERSONAS))
        logger.info("Impressions données : session %s, %d persona(s)", deps.session_id, len(spoken))
        return {"spoken": spoken}

    return impressions
