"""Dependencies injected into a graph: everything the nodes need goes through `GraphDeps`
(models from the factory, event bus, settings, feature ports), never through
globales."""

from dataclasses import dataclass
from typing import Protocol

from langchain_core.language_models import BaseChatModel
from langgraph.func import task
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.bus import EventBus
from app.agents.runtime.ports import NO_PORTS, AgentPorts
from app.agents.runtime.repositories import EventRepository
from app.agents.runtime.run_settings import RunSettings
from app.agents.runtime.user_input import UserInput, user_input_of
from app.agents.tools.memory_port import MemoryGateway
from app.agents.tools.web_port import WebGateway
from app.core.played import played_by
from app.providers.llm.base import Tier


class ChatModelSource(Protocol):
    """`LlmFactory` in production, a fake one in tests."""

    async def get_chat_model(
        self, user_id: str, tier: Tier, agent: str | None = None
    ) -> BaseChatModel: ...


@dataclass(frozen=True)
class GraphDeps:
    user_id: str
    session_id: str
    models: ChatModelSource
    bus: EventBus
    settings: RunSettings
    session_factory: async_sessionmaker[AsyncSession]
    ports: AgentPorts = NO_PORTS  # wired by the composition (`bootstrap.agent_ports`, D82)

    @property
    def memory(self) -> MemoryGateway:
        return self.ports.memory

    @property
    def web(self) -> WebGateway:
        return self.ports.web

    async def user_inputs_since(self, seq: int) -> list[UserInput]:
        """The session's `user.message` events after `seq` (text and command), in
        l'ordre."""

        async def read_messages() -> list[tuple[int, dict[str, object]]]:
            async with self.session_factory() as db:
                rows = await EventRepository(db, self.user_id).list_after(self.session_id, seq)
            return [(row.seq, row.payload) for row in rows if row.type == "user.message"]

        # On node replay, the answer covers the messages present when the brief was emitted.
        # A command that arrived during this answer will be read at the next node.
        entries = await task(read_messages)() if played_by(self.user_id) else await read_messages()
        return [user_input_of(index, payload) for index, payload in entries]

    async def user_messages_since(self, seq: int) -> list[tuple[int, str]]:
        """`(seq, text)` of the session's `user.message` events after `seq` (demo)."""
        return [(said.seq, said.text) for said in await self.user_inputs_since(seq)]
