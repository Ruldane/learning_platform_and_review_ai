"""Translates the stream of `astream(stream_mode=["custom", "messages", "updates"])` into events.

Pure, no I/O: the runner publishes what comes out of it. Shapes checked on langgraph 1.2 (format
"v1" by default, several modes -> tuples `(mode, data)`):
- `custom`: what the node wrote to the `StreamWriter` (`emit()` -> key `EVENT_KEY`);
- `messages`: `(fragment, metadata)`; the metadata carry `langgraph_node` and those
  set by `with_config(metadata=...)` (including `agent`, see `call_with_retries`);
- `updates`: `{node: update}`, or `{"__interrupt__": (Interrupt(value, id), ...)}`.
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
    """Loads `interrupt.requested`: `interrupt_id` = `Interrupt.id`, the rest = its value
    (`kind`, `question`, `options`). `ValueError` if the value does not follow the catalog."""
    value = interrupt.value if isinstance(interrupt.value, dict) else {}
    data = {**value, "interrupt_id": interrupt.id}
    public = validate_payload("interrupt.requested", data).model_dump(mode="json")
    if value.get("kind") == "mcp_model" and "brief" in value:
        public["brief"] = value["brief"]
    return public


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
    """Only fragments being written become tokens: a complete message (already
    in the state) gets its `agent.message`, an empty fragment (reasoning, tool) shows nothing."""
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
