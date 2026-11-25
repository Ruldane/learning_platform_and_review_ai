"""`cv_capture` graph (SPEC 5.1, 5.2; D124, D125): capture of a CV, in two modes, routed by
`mode` right from `START`.

`profile` mode (6.8): the Archivist draws the master profile from the CV, the LinkedIn profile
and January's note; the code removes whatever is in no document, sets the sources of each fact
and stores a draft that January will review.

START -> load_sources -> extract -> check -> save_draft -> announce -> END

`design` mode (Designer, 6.9): the design of a template's CV, in at most three automatic
passes, then the `cv_template` question (see `cv_capture_design`).

Launched only by its routes (`POST /profile/import`, `POST /cv/templates`, `ROUTE_ONLY`).
Every port write is idempotent (SPEC 9.4)."""

from typing import Any, Literal, Self

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, model_validator

from app.agents.graphs.cv_capture_design import DESIGN_ENTRY, add_design
from app.agents.nodes.archivist_profile import (
    PROFILE_REQUEST,
    announce,
    check,
    make_extract,
    make_load_sources,
    make_save_draft,
)
from app.agents.runtime.deps import GraphDeps
from app.agents.state.cv_capture import CvCaptureState
from app.agents.tools.profile_port import MAX_NOTE_CHARS

__all__ = ["PROFILE_REQUEST", "CvCaptureInput", "build"]

MAX_DOCUMENTS = 3
PROFILE_ENTRY = "load_sources"


class CvCaptureInput(BaseModel):
    mode: Literal["profile", "design"]
    document_ids: list[str] = Field(default_factory=list, max_length=MAX_DOCUMENTS)
    note: str | None = Field(default=None, max_length=MAX_NOTE_CHARS)
    template_id: str | None = Field(default=None, min_length=1, max_length=36)

    @model_validator(mode="after")
    def _ready(self) -> Self:
        """The profile starts from at least one document; the design, from a template."""
        if self.mode == "design":
            if self.template_id is None:
                raise ValueError("The design capture starts from a template.")
        elif not self.document_ids:
            raise ValueError("The master profile starts from at least one document.")
        return self


def route_mode(state: CvCaptureState) -> str:
    return DESIGN_ENTRY if state.get("mode") == "design" else PROFILE_ENTRY


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    graph = StateGraph(CvCaptureState)
    graph.add_node("load_sources", make_load_sources(deps))
    graph.add_node("extract", make_extract(deps))
    graph.add_node("check", check)
    graph.add_node("save_draft", make_save_draft(deps))
    graph.add_node("announce", announce)
    graph.add_conditional_edges(START, route_mode, [PROFILE_ENTRY, DESIGN_ENTRY])
    for source, target in [
        ("load_sources", "extract"),
        ("extract", "check"),
        ("check", "save_draft"),
        ("save_draft", "announce"),
        ("announce", END),
    ]:
        graph.add_edge(source, target)
    add_design(graph, deps)
    return graph
