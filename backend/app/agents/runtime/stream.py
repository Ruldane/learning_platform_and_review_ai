"""Traduction du flux de `astream(stream_mode=["custom", "messages", "updates"])` en événements.

Pur, sans I/O : le runner publie ce qui en sort. Formes vérifiées sur langgraph 1.2 (format
« v1 » par défaut, plusieurs modes → tuples `(mode, donnée)`) :
- `custom` : ce que le nœud a écrit dans le `StreamWriter` (`emit()` → clé `EVENT_KEY`) ;
- `messages` : `(fragment, métadonnées)` ; les métadonnées portent `langgraph_node` et celles
  posées par `with_config(metadata=...)` (dont `agent`, voir `call_with_retries`) ;
- `updates` : `{nœud: mise à jour}`, ou `{"__interrupt__": (Interrupt(value, id), ...)}`.
"""

from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessageChunk
from langgraph.types import Interrupt

from app.agents.runtime.emit import EVENT_KEY
from app.agents.runtime.events import EventType, validate_payload
from app.agents.runtime.invoke import message_text

INTERRUPT_KEY = "__interrupt__"


@dataclass(frozen=True)
class PendingEvent:
    type: EventType
    agent: str | None
    payload: dict[str, Any]


def interrupt_payload(interrupt: Interrupt) -> dict[str, Any]:
    """Charge `interrupt.requested` : `interrupt_id` = `Interrupt.id`, le reste = sa valeur
    (`kind`, `question`, `options`). `ValueError` si la valeur ne suit pas le catalogue."""
    value = interrupt.value if isinstance(interrupt.value, dict) else {}
    data = {**value, "interrupt_id": interrupt.id}
    return validate_payload("interrupt.requested", data).model_dump(mode="json")


def interrupts_of(mode: str, chunk: Any) -> tuple[Interrupt, ...]:
    if mode != "updates" or not isinstance(chunk, dict):
        return ()
    found = chunk.get(INTERRUPT_KEY) or ()
    return tuple(item for item in found if isinstance(item, Interrupt))


def _custom(chunk: Any) -> list[PendingEvent]:
    if not isinstance(chunk, dict) or EVENT_KEY not in chunk:
        return []
    return [PendingEvent(chunk[EVENT_KEY], chunk.get("agent"), dict(chunk.get("payload") or {}))]


def _message(chunk: Any) -> list[PendingEvent]:
    """Seuls les fragments en cours d'écriture deviennent des tokens : un message complet (déjà
    dans l'état) a son `agent.message`, un fragment vide (raisonnement, outil) n'affiche rien."""
    if not isinstance(chunk, tuple) or len(chunk) != 2:
        return []
    message, metadata = chunk
    if not isinstance(message, AIMessageChunk):
        return []
    text = message_text(message)
    if not text:
        return []
    meta = metadata if isinstance(metadata, dict) else {}
    agent = meta.get("agent") or meta.get("langgraph_node")
    payload = {"message_id": message.id or "", "text": text}
    return [PendingEvent("agent.token", agent, payload)]


def translate_chunk(mode: str, chunk: Any) -> list[PendingEvent]:
    if mode == "custom":
        return _custom(chunk)
    if mode == "messages":
        return _message(chunk)
    return [
        PendingEvent("interrupt.requested", None, interrupt_payload(interrupt))
        for interrupt in interrupts_of(mode, chunk)
    ]
