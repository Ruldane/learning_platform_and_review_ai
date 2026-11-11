"""Émission d'événements depuis un nœud de graphe, par le `StreamWriter` de LangGraph.

Le runner (mode `custom` de `astream`) reconnaît la clé `EVENT_KEY` et publie l'événement sur le
bus : un nœud n'a donc jamais besoin du bus ni de l'identifiant de session.
"""

from typing import Any

from langgraph.config import get_stream_writer
from pydantic import BaseModel

from app.agents.runtime.events import EventType, validate_payload

EVENT_KEY = "__tremplin_event__"


def emit(type: EventType, payload: BaseModel | dict[str, Any], *, agent: str | None = None) -> None:
    """Valide la charge tout de suite (`ValueError` si elle ne suit pas le catalogue), puis
    écrit `{EVENT_KEY: type, "agent": agent, "payload": dict}`. `RuntimeError` hors d'un nœud."""
    data = validate_payload(type, payload).model_dump(mode="json")
    try:
        writer = get_stream_writer()
    except RuntimeError:
        raise RuntimeError("emit() appelé hors d'un nœud") from None
    writer({EVENT_KEY: type, "agent": agent, "payload": data})
