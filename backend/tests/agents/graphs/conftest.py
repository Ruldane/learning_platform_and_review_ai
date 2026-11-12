from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AsyncExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.bus import EventBus
from app.agents.runtime.checkpointer import open_checkpointer
from app.agents.runtime.costs import ModelPrice
from app.agents.runtime.ports import AgentPorts
from app.agents.runtime.run_settings import RunSettings
from app.agents.runtime.runner import SessionRunner
from app.agents.tools.council_port import NO_COUNCIL, CouncilStore
from app.core.providers import MemoryProviders
from app.features.memory.service.gateway import AgentMemoryGateway
from app.features.memory.service.runtime import MemoryRuntime, memory_runtime
from app.features.research.service.gateway import AgentWebGateway
from app.providers.llm.fake import FakeLlmProvider
from app.providers.search.fake import FakeSearch
from tests.agents.graphs.council_support import make_council_runner  # noqa: F401
from tests.agents.graphs.web_support import MakeWeb, Web, add_users, research_runtime
from tests.agents.runtime.conftest import emitted  # noqa: F401  (fixture partagée)
from tests.agents.runtime.runner_helpers import fake_llm_with_provider
from tests.support.memory import FakeWebReader


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


# --- Parcours `learned_document` : vraie mémoire (base, HashingEmbedder, Qdrant local) ----------


@dataclass
class Learned:
    runner: SessionRunner
    fake: FakeLlmProvider
    memory: MemoryRuntime
    factory: async_sessionmaker[AsyncSession]
    providers: MemoryProviders


type MakeLearned = Callable[[list[str]], Awaitable[Learned]]


@pytest.fixture
async def make_learned_runner(
    tmp_path: Path,
    db_session_factory: async_sessionmaker[AsyncSession],
    memory_providers: MemoryProviders,
) -> AsyncIterator[MakeLearned]:
    """Runner sur le registre RÉEL, le faux fournisseur scripté avec `replies` et la passerelle
    mémoire réelle (base de test, `HashingEmbedder`, Qdrant en mémoire)."""
    async with AsyncExitStack() as stack:

        async def make(replies: list[str]) -> Learned:
            memory = await stack.enter_async_context(
                memory_runtime(db_session_factory, memory_providers)
            )
            saver = await stack.enter_async_context(open_checkpointer(tmp_path / "checkpoints.db"))
            bus = EventBus(db_session_factory)
            models, fake = fake_llm_with_provider(replies)
            runner = SessionRunner(
                session_factory=db_session_factory,
                bus=bus,
                models=models,
                checkpointer=saver,
                prices={"modele-test": ModelPrice(1.0, 2.0)},
                run_settings=FixedSettings(2),
                ports=AgentPorts(memory=AgentMemoryGateway(memory)),
            )
            stack.push_async_callback(bus.aclose)
            stack.push_async_callback(runner.shutdown)
            return Learned(runner, fake, memory, db_session_factory, memory_providers)

        yield make


# --- Parcours `web_research` : vraie mémoire et vraie recherche, faux moteurs et faux lecteur ----


@pytest.fixture
async def make_web_runner(
    tmp_path: Path,
    db_session_factory: async_sessionmaker[AsyncSession],
    memory_providers: MemoryProviders,
    user_id: str,
    other_user_id: str,
) -> AsyncIterator[MakeWeb]:
    """Runner sur le registre RÉEL. Plusieurs appels = plusieurs processus (même base, même
    `checkpoints.db`, mêmes faux moteurs). `models` remplace le faux LLM ; `council` : le port."""
    search, reader = FakeSearch("searxng"), FakeWebReader()
    await add_users(db_session_factory, user_id, other_user_id)
    research = research_runtime(db_session_factory, search, reader)
    async with AsyncExitStack() as stack:

        async def make(
            replies: list[str], *, models: Any = None, council: CouncilStore = NO_COUNCIL
        ) -> Web:
            memory = await stack.enter_async_context(
                memory_runtime(db_session_factory, memory_providers)
            )
            saver = await stack.enter_async_context(open_checkpointer(tmp_path / "checkpoints.db"))
            bus = EventBus(db_session_factory)
            fake = None
            if models is None:
                models, fake = fake_llm_with_provider(replies)
            web = Web(
                None,  # type: ignore[arg-type]
                fake,
                memory,
                db_session_factory,
                search,
                reader,
                research,
                AgentWebGateway(research),
                AgentMemoryGateway(memory),
            )
            web.runner = SessionRunner(
                session_factory=db_session_factory,
                bus=bus,
                models=models,
                checkpointer=saver,
                prices={"modele-test": ModelPrice(1.0, 2.0)},
                run_settings=FixedSettings(2),
                ports=AgentPorts(memory=web.memory_gateway, web=web.gateway, council=council),
            )
            stack.push_async_callback(bus.aclose)
            stack.push_async_callback(web.runner.shutdown)
            return web

        yield make
