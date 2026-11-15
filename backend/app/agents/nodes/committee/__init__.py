"""Le comité de recrutement simulé (SPEC F19, D147) : quatre personas (Lecteur ATS, Recruteur,
Manager, Futur collègue) donnent leur impression, débattent deux tours, votent ; le Modérateur
classe les objections et propose trois changements. Utilisé par le parcours `hiring_committee`."""

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
