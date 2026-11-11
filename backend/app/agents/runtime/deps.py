"""Dépendances injectées dans un graphe : tout ce dont les nœuds ont besoin passe par `GraphDeps`
(modèles par la fabrique, bus d'événements, réglages), jamais par des globales."""

from dataclasses import dataclass
from typing import Protocol

from langchain_core.language_models import BaseChatModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.bus import EventBus
from app.agents.runtime.repositories import EventRepository
from app.agents.runtime.run_settings import RunSettings
from app.providers.llm.base import Tier


class ChatModelSource(Protocol):
    """`LlmFactory` en production, un faux en test."""

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

    async def user_messages_since(self, seq: int) -> list[tuple[int, str]]:
        """`(seq, texte)` des `user.message` de la session au-delà de `seq`, dans l'ordre."""
        async with self.session_factory() as db:
            rows = await EventRepository(db, self.user_id).list_after(self.session_id, seq)
        return [
            (row.seq, str(row.payload.get("text", "")))
            for row in rows
            if row.type == "user.message"
        ]
