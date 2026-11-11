"""`AgentRuntime` : poignée du moteur d'agents posée sur `app.state.runtime` par le lifespan.

Module léger (aucun import de LangGraph ni du runner à l'exécution) : `app.core.deps` peut
l'importer sans charger tout le moteur.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.agents.runtime.bus import EventBus
    from app.agents.runtime.runner import SessionRunner


@dataclass(frozen=True)
class AgentRuntime:
    bus: EventBus
    runner: SessionRunner
