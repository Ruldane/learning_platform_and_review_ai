"""The Strategist (SPEC 9.1): architect of the learning path. It debates (shared node
`debate_turn`), proposes the paths (`propose`) and writes the program (`plan`, `program_builder`
graph)."""

from app.agents.nodes.strategist.propose import (
    AGENT,
    MAX_PROPOSALS,
    MIN_PROPOSALS,
    ProposalSet,
    make_propose,
)

__all__ = ["AGENT", "MAX_PROPOSALS", "MIN_PROPOSALS", "ProposalSet", "make_propose"]
