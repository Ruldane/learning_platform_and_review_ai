"""Lecture et rangement du comité de recrutement (SPEC F19, D147) : `load` lit le contexte par le
port (lecture seule), `save` range l'issue — les quatre votes, le verdict, les objections et les
trois changements — par le port, **idempotent par session** (SPEC 9.4) : le seul nœud qui écrit.
Un nœud rejoué après un arrêt relit l'issue de sa session et ne range rien une seconde fois.

Journaux : identifiants et nombres seulement, jamais le CV, l'offre, une parole ni l'entreprise
(17.2)."""

import logging

from app.agents.nodes.committee.common import Node
from app.agents.nodes.committee.synthesis import AGENT
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.state.hiring_committee import HiringCommitteeState
from app.agents.tools.committee_schema import VERDICT_WORDS, PersonaVote, Synthesis

logger = logging.getLogger(__name__)


def make_load(deps: GraphDeps) -> Node:
    @node_timeout()
    async def load(state: HiringCommitteeState) -> HiringCommitteeState:
        ctx = await deps.ports.committee.context(deps.user_id, state["run_id"])
        logger.info(
            "Comité lu : session %s, exécution %s, taille %s",
            deps.session_id,
            state["run_id"],
            ctx.size,
        )
        return {"context": ctx.model_dump(mode="json")}

    return load


def make_save(deps: GraphDeps) -> Node:
    @node_timeout()
    async def save(state: HiringCommitteeState) -> HiringCommitteeState:
        """L'issue du comité, la seule écriture ; rejoué, le port relit celle de la session."""
        votes = [PersonaVote.model_validate(v) for v in state["votes"]]
        synthesis = Synthesis.model_validate(state["synthesis"])
        await deps.ports.committee.save_result(
            deps.user_id, deps.session_id, state["run_id"], votes, synthesis
        )
        logger.info(
            "Comité rangé : session %s, exécution %s, verdict %s",
            deps.session_id,
            state["run_id"],
            synthesis.verdict,
        )
        text = (
            f"Comité terminé : verdict {VERDICT_WORDS[synthesis.verdict]}, "
            f"{len(synthesis.objections)} objection(s), {len(synthesis.changes)} changements "
            "proposés. C'est une simulation, pas une prédiction."
        )
        emit("agent.message", {"message_id": f"{AGENT}-fin", "text": text}, agent=AGENT)
        return {"summary": text}

    return save
