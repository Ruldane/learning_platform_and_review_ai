"""The Scout (SPEC 9.1): prepares the queries, searches, reads, scores the sources out of 100 and
keeps the selected ones in memory. Used by the `web_research` flow (test bench, then Council)."""

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
