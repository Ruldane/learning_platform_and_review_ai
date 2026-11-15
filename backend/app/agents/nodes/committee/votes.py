"""Les votes du comité (SPEC F19, D147) : après le débat, chaque persona vote — entretien oui, non
ou peut-être — avec son objection principale. Les quatre votes sont indépendants : ils partent
ensemble, chacun sur tout ce qui s'est dit. Une fois dans l'état (checkpointer), un vote n'est
jamais redemandé : le nœud terminé n'est pas rejoué après un redémarrage. Aucune écriture en base.
Un vote illisible après les nouveaux essais fait échouer la session : un vote de repli serait un
avis que personne n'a donné."""

import logging
from typing import Any

from app.agents.nodes.committee.common import (
    TURN_TIMEOUT_S,
    VOTE_REQUEST,
    Node,
    context_of,
    persona_call,
    together,
)
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.hiring_committee import HiringCommitteeState
from app.agents.tools.committee_schema import (
    PERSONAS,
    CommitteeContext,
    Persona,
    PersonaVote,
    Vote,
)

VOTE_WORDS = {
    "oui": "oui, je donnerais un entretien",
    "non": "non, je n'irais pas plus loin",
    "peut_etre": "peut-être, je veux en savoir plus",
}

logger = logging.getLogger(__name__)


async def _vote(
    deps: GraphDeps, ctx: CommitteeContext, spoken: list[dict[str, Any]], persona: Persona
) -> PersonaVote:
    model, messages = await persona_call(deps, ctx, persona, "vote", VOTE_REQUEST, spoken=spoken)
    found = await structured_call(
        model, Vote, messages, agent=persona, step="vote", intent="je vote"
    )
    vote = PersonaVote(persona=persona, **found.model_dump())
    text = f"Mon vote : {VOTE_WORDS[vote.vote]}.\nObjection principale : {vote.objection}"
    emit("agent.message", {"message_id": f"{persona}-vote", "text": text}, agent=persona)
    return vote


def make_votes(deps: GraphDeps) -> Node:
    @node_timeout(TURN_TIMEOUT_S)
    async def votes(state: HiringCommitteeState) -> HiringCommitteeState:
        """Les quatre votes, dans l'ordre des personas."""
        ctx = context_of(state)
        spoken = list(state["spoken"])
        cast = await together(*(_vote(deps, ctx, spoken, p) for p in PERSONAS))
        logger.info(
            "Votes rendus : session %s, %s",
            deps.session_id,
            ", ".join(f"{vote.persona}={vote.vote}" for vote in cast),
        )
        return {"votes": [vote.model_dump(mode="json") for vote in cast]}

    return votes
