"""Le Stratège (SPEC 9.1) : architecte du parcours. Il débat (nœud commun `debate_turn`), propose
les parcours (`propose`) et, en 4.5, écrit le programme."""

from app.agents.nodes.strategist.propose import (
    AGENT,
    MAX_PROPOSALS,
    MIN_PROPOSALS,
    ProposalSet,
    make_propose,
)

__all__ = ["AGENT", "MAX_PROPOSALS", "MIN_PROPOSALS", "ProposalSet", "make_propose"]
