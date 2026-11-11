import asyncio
from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.bus import EventBus
from app.agents.runtime.events import SessionEvent
from app.agents.runtime.repositories import SessionRepository

TIMEOUT = 5.0


@pytest.fixture
def bus(db_factory: async_sessionmaker[AsyncSession]) -> EventBus:
    return EventBus(db_factory)


@pytest.fixture
async def session_id(db_factory: async_sessionmaker[AsyncSession], user_id: str) -> str:
    async with db_factory() as db:
        row = await SessionRepository(db, user_id).add(graph="demo", status="running", input={})
        await db.commit()
    return row.id


async def say(bus: EventBus, user_id: str, session_id: str, text: str) -> SessionEvent:
    """Publie un `user.message` (charge la plus simple du catalogue)."""
    return await bus.publish(
        user_id=user_id, session_id=session_id, type="user.message", payload={"text": text}
    )


async def take(it: AsyncIterator[SessionEvent], count: int) -> list[int]:
    """Lit `count` événements (avec délai maximal) et renvoie leurs `seq`."""
    return [(await asyncio.wait_for(anext(it), TIMEOUT)).seq for _ in range(count)]


@pytest.fixture
def emitted(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, object]]:
    """Remplace le `StreamWriter` de LangGraph : `emit()` marche hors d'un graphe et les tests
    lisent ce qui a été émis."""
    written: list[dict[str, object]] = []
    monkeypatch.setattr("app.agents.runtime.emit.get_stream_writer", lambda: written.append)
    return written
