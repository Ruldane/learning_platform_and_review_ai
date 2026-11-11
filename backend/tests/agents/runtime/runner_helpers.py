"""Outils des tests du runner : fabrique LLM sur le faux fournisseur, attentes sur conditions
(jamais sur une durée : chaque attente sonde un état, avec un délai maximal), lectures."""

import asyncio
from collections.abc import Callable
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.bus_state import to_event
from app.agents.runtime.events import SessionEvent
from app.agents.runtime.repositories import EventRepository, SessionRepository
from app.agents.runtime.runner import SessionRunner
from app.db.models.agents import AgentSession
from app.providers.llm.base import ModelChoice, Tier
from app.providers.llm.factory import LlmFactory
from app.providers.llm.fake import FakeLlmProvider

type Factory = async_sessionmaker[AsyncSession]

TIMEOUT = 5.0


class _FakeChoice:
    async def get_model_choice(self, user_id: str, tier: Tier, agent: str | None) -> ModelChoice:
        return ModelChoice(provider="fake", model="modele-test")


class _Keys:
    def __init__(self, key: str | None) -> None:
        self._key = key

    async def get_key(self, user_id: str, provider: str) -> str | None:
        return self._key


def fake_llm(replies: list[str], *, key: str | None = "fake-key") -> LlmFactory:
    """La vraie fabrique, branchée sur le faux fournisseur ; `key=None` : clé absente."""
    provider = FakeLlmProvider(replies)
    return LlmFactory(_FakeChoice(), _Keys(key), {"fake": provider}, {})


async def wait_until(predicate: Callable[[], bool]) -> None:
    async with asyncio.timeout(TIMEOUT):
        while not predicate():
            await asyncio.sleep(0.01)


async def get_session(db: Factory, user_id: str, session_id: str) -> AgentSession:
    async with db() as session:
        row = await SessionRepository(session, user_id).get(session_id)
    assert row is not None
    return row


async def wait_status(db: Factory, user_id: str, session_id: str, status: str) -> AgentSession:
    async with asyncio.timeout(TIMEOUT):
        while (row := await get_session(db, user_id, session_id)).status != status:
            await asyncio.sleep(0.01)
    return row


async def wait_idle(runner: SessionRunner, session_id: str) -> None:
    """La tâche de la session a fini (issue écrite et publiée)."""
    await wait_until(lambda: not runner.is_active(session_id))


async def all_events(db: Factory, user_id: str, session_id: str) -> list[SessionEvent]:
    async with db() as session:
        rows = await EventRepository(session, user_id).list_after(session_id, 0)
    return [to_event(row) for row in rows]


async def types(db: Factory, user_id: str, session_id: str) -> list[str]:
    return [e.type for e in await all_events(db, user_id, session_id)]


async def final_state(checkpointer: BaseCheckpointSaver[Any], session_id: str) -> dict[str, Any]:
    saved = await checkpointer.aget_tuple({"configurable": {"thread_id": session_id}})
    assert saved is not None
    return dict(saved.checkpoint["channel_values"])
