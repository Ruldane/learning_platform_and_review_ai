"""Le Stratège (SPEC 9.1) : architecte du parcours. Il débat (nœud commun `debate_turn`), propose
les parcours (`propose`) et écrit le programme (`plan`, parcours `program_builder`)."""

from app.agents.nodes.strategist.propose import (
    AGENT,
    MAX_PROPOSALS,
    MIN_PROPOSALS,
    ProposalSet,
    make_propose,
)

__all__ = ["AGENT", "MAX_PROPOSALS", "MIN_PROPOSALS", "ProposalSet", "make_propose"]
