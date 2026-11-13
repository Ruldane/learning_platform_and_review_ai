"""Parcours `capture` (SPEC F18, D108) : un lien, un document importé ou une note de January
devient un élément de mémoire `document` résumé en cinq lignes, relié à ses modules ; l'Archiviste
propose ensuite de cocher la tâche que la capture couvre, puis de créer des fiches.

START -> read -> (illisible ? ask_text : digest)
ask_text -> (texte ? digest : END « Capture abandonnée. »)
digest -> store -> (tâche couverte ? ask_task : after_task)
ask_task -> (oui ? tick : after_task) ; tick -> after_task
after_task -> (fiches ? ask_cards : finalize) ; ask_cards -> (oui ? cards : finalize)
cards -> finalize -> END

Trois points d'arrêt (`ask_text`, `ask_task`, `ask_cards`), chacun seul dans son nœud (SPEC 9.4).
Les écritures du port (`store`, `tick_task`, `add_cards`) sont idempotentes."""

from typing import Any, Self

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field, model_validator

from app.agents.nodes.archivist_capture import (
    after_task,
    ask_cards,
    ask_task,
    ask_text,
    finalize,
    make_cards,
    make_digest,
    make_read,
    make_store,
    make_tick,
    route_after_task,
    route_cards,
    route_read,
    route_store,
    route_task,
    route_text,
)
from app.agents.nodes.archivist_capture_steps import (
    CANCELLED_TEXT,
    CAPTURE_CARDS,
    CAPTURE_TASK,
    CAPTURE_TEXT,
    TEXT_INTERRUPT,
    UNREADABLE_TEXT,
)
from app.agents.runtime.deps import GraphDeps
from app.agents.state.capture import CaptureState

__all__ = [
    "CANCELLED_TEXT",
    "CAPTURE_CARDS",
    "CAPTURE_TASK",
    "CAPTURE_TEXT",
    "TEXT_INTERRUPT",
    "UNREADABLE_TEXT",
    "CaptureInput",
    "build",
]


class CaptureInput(BaseModel):
    url: str | None = Field(default=None, max_length=2048)
    text: str | None = Field(default=None, max_length=20000)
    document_id: str | None = Field(default=None, max_length=36)

    @model_validator(mode="after")
    def _one_source(self) -> Self:
        """Un seul des trois, non vide (422 `invalid_input` sinon)."""
        given = [v for v in (self.url, self.text, self.document_id) if v is not None and v.strip()]
        if len(given) != 1:
            raise ValueError("Une capture demande une seule source : lien, texte ou document.")
        return self


def build(deps: GraphDeps) -> StateGraph[Any, Any, Any, Any]:
    graph = StateGraph(CaptureState)
    graph.add_node("read", make_read(deps))
    graph.add_node("ask_text", ask_text)
    graph.add_node("digest", make_digest(deps))
    graph.add_node("store", make_store(deps))
    graph.add_node("ask_task", ask_task)
    graph.add_node("tick", make_tick(deps))
    graph.add_node("after_task", after_task)
    graph.add_node("ask_cards", ask_cards)
    graph.add_node("cards", make_cards(deps))
    graph.add_node("finalize", finalize)
    for source, target in [
        (START, "read"),
        ("digest", "store"),
        ("tick", "after_task"),
        ("cards", "finalize"),
        ("finalize", END),
    ]:
        graph.add_edge(source, target)
    graph.add_conditional_edges("read", route_read, ["ask_text", "digest"])
    graph.add_conditional_edges("ask_text", route_text, {"digest": "digest", "end": END})
    graph.add_conditional_edges("store", route_store, ["ask_task", "after_task"])
    graph.add_conditional_edges("ask_task", route_task, ["tick", "after_task"])
    graph.add_conditional_edges("after_task", route_after_task, ["ask_cards", "finalize"])
    graph.add_conditional_edges("ask_cards", route_cards, ["cards", "finalize"])
    return graph
