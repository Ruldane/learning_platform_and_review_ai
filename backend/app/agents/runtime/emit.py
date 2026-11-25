"""Event emission from a graph node, through LangGraph's `StreamWriter`.

The runner (`custom` mode of `astream`) recognises the `EVENT_KEY` key and publishes the event on
the bus: a node therefore never needs the bus or the session identifier.
"""

from typing import Any

from langgraph.config import get_stream_writer
from pydantic import BaseModel

from app.agents.runtime.events import EventType, validate_payload

EVENT_KEY = "__tremplin_event__"


def emit(type: EventType, payload: BaseModel | dict[str, Any], *, agent: str | None = None) -> None:
    """Validates the payload right away (`ValueError` if it does not follow the catalogue), then
    writes `{EVENT_KEY: type, "agent": agent, "payload": dict}`. `RuntimeError` outside a node."""
    data = validate_payload(type, payload).model_dump(mode="json")
    try:
        writer = get_stream_writer()
    except RuntimeError:
        raise RuntimeError("emit() called outside a node") from None
    writer({EVENT_KEY: type, "agent": agent, "payload": data})
