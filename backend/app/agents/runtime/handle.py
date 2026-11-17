"""`AgentRuntime` : poignée du moteur d'agents posée sur `app.state.runtime` par le lifespan.

Module léger (aucun import de LangGraph ni du runner à l'exécution) : `app.core.deps` peut
l'importer sans charger tout le moteur.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.agents.runtime.bus import EventBus
    from app.agents.runtime.runner import SessionRunner


@dataclass(frozen=True)
class AgentRuntime:
    bus: EventBus
    runner: SessionRunner

    async def delete_threads(self, session_ids: Iterable[str]) -> None:
        """Efface les points de reprise de ces sessions (`SessionRunner.delete_threads`)."""
        await self.runner.delete_threads(session_ids)
