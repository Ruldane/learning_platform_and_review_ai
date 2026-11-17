"""`AgentRuntime` : poignée du moteur d'agents posée sur `app.state.runtime` par le lifespan.

Module léger (aucun import de LangGraph ni du runner à l'exécution) : `app.core.deps` peut
l'importer sans charger tout le moteur.
"""

from __future__ import annotations

from collections.abc import Iterable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.agents.runtime.bus import EventBus
    from app.agents.runtime.runner import SessionRunner
    from app.db.models.agents import AgentSession


@dataclass(frozen=True)
class AgentRuntime:
    bus: EventBus
    runner: SessionRunner

    async def delete_threads(self, session_ids: Iterable[str]) -> None:
        """Efface les points de reprise de ces sessions (`SessionRunner.delete_threads`)."""
        await self.runner.delete_threads(session_ids)

    async def open_sessions(self, user_id: str) -> list[str]:
        """Les sessions ouvertes de ce compte (`SessionRunner.open_sessions`)."""
        return await self.runner.open_sessions(user_id)

    async def cancel(self, user_id: str, session_id: str) -> AgentSession:
        """Annule une session du compte (`SessionRunner.cancel`)."""
        return await self.runner.cancel(user_id, session_id)

    def refusing_starts(self, user_id: str) -> AbstractAsyncContextManager[None]:
        """Aucune session de ce compte ne démarre le temps du bloc (`SessionRunner`)."""
        return self.runner.refusing_starts(user_id)
