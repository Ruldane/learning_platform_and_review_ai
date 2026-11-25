"""`AgentRuntime`: handle of the agent engine set on `app.state.runtime` by the lifespan.

Lightweight module (no import of LangGraph nor of the runner at execution time): `app.core.deps`
can import it without loading the whole engine.
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
        """Clears the resume points of these sessions (`SessionRunner.delete_threads`)."""
        await self.runner.delete_threads(session_ids)

    async def open_sessions(self, user_id: str) -> list[str]:
        """The open sessions of this account (`SessionRunner.open_sessions`)."""
        return await self.runner.open_sessions(user_id)

    async def cancel(self, user_id: str, session_id: str) -> AgentSession:
        """Cancels a session of the account (`SessionRunner.cancel`)."""
        return await self.runner.cancel(user_id, session_id)

    def refusing_starts(self, user_id: str) -> AbstractAsyncContextManager[None]:
        """No session of this account starts for the duration of the block (`SessionRunner`)."""
        return self.runner.refusing_starts(user_id)
