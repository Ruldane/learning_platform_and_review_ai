"""L'Éclaireur (SPEC 9.1) : prépare les requêtes, cherche, lit, note les sources sur 100 et garde
les retenues en mémoire. Utilisé par le parcours `web_research` (banc d'essai, puis le Conseil)."""

from app.agents.nodes.scout.assess import finalize, make_judge, make_remember
from app.agents.nodes.scout.gather import make_plan, make_read, make_search
from app.agents.nodes.scout.models import (
    AGENT,
    MAX_PAGES_PER_RUN,
    PAGE_CHARS_FOR_SCORING,
    PlannedQuery,
    SearchPlan,
    SourceScore,
)

__all__ = [
    "AGENT",
    "MAX_PAGES_PER_RUN",
    "PAGE_CHARS_FOR_SCORING",
    "PlannedQuery",
    "SearchPlan",
    "SourceScore",
    "finalize",
    "make_judge",
    "make_plan",
    "make_read",
    "make_remember",
    "make_search",
]
