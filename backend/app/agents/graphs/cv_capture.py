"""Parcours `cv_capture` (SPEC 5.1, 5.2 ; D124) : capture d'un CV, en deux modes.

Mode `profile` (6.8) : l'Archiviste tire le profil maître du CV, du profil LinkedIn et de la note
de January ; le code retire ce qui n'est dans aucun document, pose les sources de chaque fait et
range un brouillon que January relira.

START -> load_sources -> extract -> check -> save_draft -> announce -> END

Mode `design` (Maquettiste) : aiguillé par `mode` en 6.9 ; refusé à l'entrée d'ici là.

Lancé seulement par sa route (`POST /profile/import`, `ROUTE_ONLY`). Aucun point d'arrêt ;
`save_draft` est idempotent par session (SPEC 9.4)."""

from typing import Any, Literal, Self

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, model_validator

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


class CvCaptureInput(BaseModel):
    mode: Literal["profile", "design"]
    document_ids: list[str] = Field(default_factory=list, max_length=MAX_DOCUMENTS)
    note: str | None = Field(default=None, max_length=MAX_NOTE_CHARS)
    template_id: str | None = None

    @model_validator(mode="after")
    def _ready(self) -> Self:
        """Le profil part d'au moins un document ; le design attend le Maquettiste (6.9)."""
        if self.mode == "design":
            raise ValueError("La capture du design n'est pas encore disponible.")
        if not self.document_ids:
            raise ValueError("Le profil maître part d'au moins un document.")
        return self


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    graph = StateGraph(CvCaptureState)
    graph.add_node("load_sources", make_load_sources(deps))
    graph.add_node("extract", make_extract(deps))
    graph.add_node("check", check)
    graph.add_node("save_draft", make_save_draft(deps))
    graph.add_node("announce", announce)
    for source, target in [
        (START, "load_sources"),
        ("load_sources", "extract"),
        ("extract", "check"),
        ("check", "save_draft"),
        ("save_draft", "announce"),
        ("announce", END),
    ]:
        graph.add_edge(source, target)
    return graph
