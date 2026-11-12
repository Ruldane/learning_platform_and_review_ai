"""Le Stratège propose 2 à 3 parcours (SPEC 3.1, étape 5, D85), par lot : un nouveau tour de
débat demandé au moment du choix donne un nouveau lot. Il part du compte rendu du Scribe (sortie
d'agent, encadrée), des messages de January, de l'objectif et du cadrage.

Le port enregistre le lot de façon idempotente par `(session, lot)` : le nœud rejoué rappelle le
modèle mais retrouve le lot déjà écrit, jamais un second."""

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
from app.agents.tools.council_port import ProposalDraft, ProposalRef

AGENT = "strategist"
MIN_PROPOSALS = 2
MAX_PROPOSALS = 3


class ProposalSet(BaseModel):
    proposals: list[ProposalDraft] = Field(min_length=MIN_PROPOSALS, max_length=MAX_PROPOSALS)


def _prompt(state: CouncilState) -> str:
    minutes = state.get("minutes") or "Pas de compte rendu."
    return render_prompt(
        AGENT,
        mode="propose",
        **goal_vars(state),
        minutes=untrusted(minutes, "compte rendu du Scribe"),
        notes=notes_prompt(state.get("notes", [])),
        min_proposals=MIN_PROPOSALS,
        max_proposals=MAX_PROPOSALS,
    )


def _state_entries(refs: list[ProposalRef], drafts: list[ProposalDraft]) -> list[dict[str, Any]]:
    """Le lot tel que le port l'a écrit (ids, rangs, noms), complété des détails rédigés."""
    by_rank = {rank: draft for rank, draft in enumerate(drafts, start=1)}
    entries = []
    for ref in refs:
        draft = by_rank.get(ref.rank)
        details = draft.model_dump() if draft is not None else {}
        entries.append(
            {**details, "proposal_id": ref.proposal_id, "rank": ref.rank, "name": ref.name}
        )
    return entries


def make_propose(deps: GraphDeps) -> Node:
    @node_timeout()
    async def propose(state: CouncilState) -> CouncilState:
        batch = state.get("batch", 0) + 1
        model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
        found = await structured_call(
            model,
            ProposalSet,
            [SystemMessage(_prompt(state)), HumanMessage("Propose les parcours.")],
            agent=AGENT,
            step=f"propositions-{batch}",
            intent="je propose des parcours",
        )
        refs = await deps.ports.council.save_proposals(
            deps.user_id,
            deps.session_id,
            state["goal_id"],
            batch=batch,
            proposals=found.proposals,
        )
        for ref in refs:
            emit("proposal.ready", {"proposal_id": ref.proposal_id, "title": ref.name}, agent=AGENT)
        return {"batch": batch, "proposals": _state_entries(refs, found.proposals), "choice": None}

    return propose
