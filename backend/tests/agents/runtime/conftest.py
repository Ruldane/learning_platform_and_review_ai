import asyncio
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any

import pytest
from langgraph.checkpoint.base import BaseCheckpointSaver
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.bus import EventBus
from app.agents.runtime.checkpointer import open_checkpointer
from app.agents.runtime.costs import ModelPrice
from app.agents.runtime.deps import ChatModelSource
from app.agents.runtime.events import SessionEvent
from app.agents.runtime.repositories import SessionRepository
from app.agents.runtime.runner import SessionRunner
from app.features.settings.service import SettingsRunReader
from tests.agents.graphs_for_tests import TEST_GRAPHS, Probe, reset_probe
from tests.agents.runtime.runner_helpers import fake_llm

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


# --- Runner ---------------------------------------------------------------------------------


@pytest.fixture
async def checkpointer(tmp_path: Path) -> AsyncIterator[BaseCheckpointSaver[Any]]:
    async with open_checkpointer(tmp_path / "donnees" / "checkpoints.db") as saver:
        yield saver


@pytest.fixture
def probe() -> Probe:
    return reset_probe()


@pytest.fixture
async def make_runner(
    db_factory: async_sessionmaker[AsyncSession],
    bus: EventBus,
    checkpointer: BaseCheckpointSaver[Any],
    probe: Probe,
) -> AsyncIterator[Callable[[ChatModelSource], SessionRunner]]:
    """Runners sur la base, le bus et le checkpointer du test ; arrêtés en fin de test."""
    made: list[SessionRunner] = []

    def make(models: ChatModelSource) -> SessionRunner:
        runner = SessionRunner(
            session_factory=db_factory,
            bus=bus,
            models=models,
            checkpointer=checkpointer,
            prices={"modele-test": ModelPrice(1.0, 2.0)},
            run_settings=SettingsRunReader(db_factory),
            graphs=TEST_GRAPHS,
        )
        made.append(runner)
        return runner

    yield make
    probe.release_b.set()
    for runner in made:
        await runner.shutdown()
    await bus.aclose()


@pytest.fixture
def runner(make_runner: Callable[[ChatModelSource], SessionRunner]) -> SessionRunner:
    return make_runner(fake_llm(["Bonjour à toi"]))
