from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AsyncExitStack
from dataclasses import dataclass
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.bus import EventBus
from app.agents.runtime.checkpointer import open_checkpointer
from app.agents.runtime.costs import ModelPrice
from app.agents.runtime.run_settings import RunSettings
from app.agents.runtime.runner import SessionRunner
from app.providers.llm.fake import FakeLlmProvider
from tests.agents.runtime.runner_helpers import fake_llm_with_provider


class FixedSettings:
    """`RunSettingsSource` de test : les réglages par défaut, `debate_rounds` au choix."""

    def __init__(self, debate_rounds: int) -> None:
        self._rounds = debate_rounds

    async def get_run_settings(self, user_id: str) -> RunSettings:
        return RunSettings(
            session_token_cap=300_000,
            debate_rounds=self._rounds,
            lesson_language="fr",
            search_languages=("fr",),
            style_guide="",
        )


@dataclass
class Debate:
    runner: SessionRunner
    fake: FakeLlmProvider


type MakeDebate = Callable[..., Awaitable[Debate]]


@pytest.fixture
async def make_debate(
    tmp_path: Path, db_factory: async_sessionmaker[AsyncSession]
) -> AsyncIterator[MakeDebate]:
    """Runner sur le registre RÉEL des parcours (`GRAPHS`), le faux fournisseur scripté avec
    `replies` et `debate_rounds` réglé. Plusieurs appels = plusieurs processus qui se suivent
    sur la même base et le même `checkpoints.db`."""
    async with AsyncExitStack() as stack:

        async def make(replies: list[str], rounds: int = 2) -> Debate:
            saver = await stack.enter_async_context(open_checkpointer(tmp_path / "checkpoints.db"))
            bus = EventBus(db_factory)
            models, fake = fake_llm_with_provider(replies)
            runner = SessionRunner(
                session_factory=db_factory,
                bus=bus,
                models=models,
                checkpointer=saver,
                prices={"modele-test": ModelPrice(1.0, 2.0)},
                run_settings=FixedSettings(rounds),
            )
            stack.push_async_callback(bus.aclose)
            stack.push_async_callback(runner.shutdown)
            return Debate(runner, fake)

        yield make
