"""Parcours `learned_document` (D68) : un document marqué « déjà appris » devient des acquis
au niveau `declare` (SPEC 4.3), écrits par l'Archiviste avec leur raison. Aucune interruption.

START -> load_context -> extract -> write -> finalize -> END
"""

from typing import Any

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from app.agents.nodes.archivist import (
    finalize,
    make_extract,
    make_load_context,
    make_write,
)
from app.agents.runtime.deps import GraphDeps
from app.agents.state.learned_document import LearnedDocumentState


class LearnedDocumentInput(BaseModel):
    document_id: str = Field(min_length=1, max_length=36)


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    graph = StateGraph(LearnedDocumentState)
    graph.add_node("load_context", make_load_context(deps))
    graph.add_node("extract", make_extract(deps))
    graph.add_node("write", make_write(deps))
    graph.add_node("finalize", finalize)
    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "extract")
    graph.add_edge("extract", "write")
    graph.add_edge("write", "finalize")
    graph.add_edge("finalize", END)
    return graph
