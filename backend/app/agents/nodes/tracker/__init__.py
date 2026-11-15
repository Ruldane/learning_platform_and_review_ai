"""L'Assistant de suivi (SPEC 9.1, F5, D141) : il lit la phrase de January (« j'ai postulé hier chez
X pour le poste Y ») et en tire une fiche de candidature en préparation, qu'elle confirme avant
la création. Utilisé par le parcours `application_intake`."""

from app.agents.nodes.tracker.confirm import ask_confirm, route_confirm
from app.agents.nodes.tracker.intake import (
    AGENT,
    INTAKE_REQUEST,
    announce,
    leave,
    make_alerts,
    make_load,
    make_parse,
    make_save,
)

__all__ = [
    "AGENT",
    "INTAKE_REQUEST",
    "announce",
    "ask_confirm",
    "leave",
    "make_alerts",
    "make_load",
    "make_parse",
    "make_save",
    "route_confirm",
]
