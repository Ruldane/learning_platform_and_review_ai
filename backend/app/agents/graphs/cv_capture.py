"""Parcours `cv_capture` (SPEC 5.1, 5.2 ; D124, D125) : capture d'un CV, en deux modes, aiguillés
par `mode` dès `START`.

Mode `profile` (6.8) : l'Archiviste tire le profil maître du CV, du profil LinkedIn et de la note
de January ; le code retire ce qui n'est dans aucun document, pose les sources de chaque fait et
range un brouillon que January relira.

START -> load_sources -> extract -> check -> save_draft -> announce -> END

Mode `design` (Maquettiste, 6.9) : le design du CV d'un gabarit, en trois passes automatiques au
plus, puis la question `cv_template` (voir `cv_capture_design`).

Lancé seulement par ses routes (`POST /profile/import`, `POST /cv/templates`, `ROUTE_ONLY`).
Chaque écriture d'un port est idempotente (SPEC 9.4)."""

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
        """Le profil part d'au moins un document ; le design, d'un gabarit."""
        if self.mode == "design":
            if self.template_id is None:
                raise ValueError("La capture du design part d'un gabarit.")
        elif not self.document_ids:
            raise ValueError("Le profil maître part d'au moins un document.")
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
