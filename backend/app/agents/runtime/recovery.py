"""Entrée à restaurer pour une réponse déjà acceptée."""

from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.pregel import Pregel
from langgraph.types import Command

from app.agents.runtime.playback import restore_delivery
from app.db.models.agents import AgentSession


async def saved_command(
    graph: Pregel[Any, Any, Any, Any], config: RunnableConfig, row: AgentSession
) -> Command[Any] | None:
    if row.play_delivery is None and row.user_delivery is None:
        return None
    pending = (await graph.aget_state(config)).interrupts
    if row.play_delivery is not None:
        return restore_delivery(pending, row.play_delivery)
    if row.user_delivery is not None:
        for item in pending:
            if item.id == row.user_delivery.get("interrupt_id"):
                return Command(resume={item.id: row.user_delivery["value"]})
    return None
