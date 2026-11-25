"""The simulated hiring committee (SPEC F19, D147): four personas (ATS Reader, Recruiter,
Manager, Future colleague) give their impression, debate for two rounds, vote; the Moderator
ranks the objections and proposes three changes. Used by the `hiring_committee` flow."""

from app.agents.nodes.committee.debate import make_round
from app.agents.nodes.committee.impressions import make_impressions
from app.agents.nodes.committee.store import make_load, make_save
from app.agents.nodes.committee.synthesis import make_synthesis
from app.agents.nodes.committee.votes import make_votes

__all__ = [
    "make_impressions",
    "make_load",
    "make_round",
    "make_save",
    "make_synthesis",
    "make_votes",
]
