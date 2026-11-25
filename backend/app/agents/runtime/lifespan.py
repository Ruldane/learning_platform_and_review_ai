"""The agent engine in the life of the application: checkpointer, bus and runner opened at
startup (with the resuming of interrupted sessions), closed in order at shutdown."""

import logging
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.bus import EventBus
from app.agents.runtime.checkpointer import open_checkpointer
from app.agents.runtime.costs import ModelPrice
from app.agents.runtime.deps import ChatModelSource
from app.agents.runtime.handle import AgentRuntime
from app.agents.runtime.ports import NO_PORTS, AgentPorts
from app.agents.runtime.run_settings import RunSettingsSource
from app.agents.runtime.runner import SessionRunner
from app.config import Settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def agent_runtime(
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    models: ChatModelSource,
    prices: Mapping[str, ModelPrice],
    run_settings: RunSettingsSource,
    *,
    ports: AgentPorts = NO_PORTS,
) -> AsyncIterator[AgentRuntime]:
    """`prices`, `run_settings` and `ports` come from the composition (`app.bootstrap`):
    `app.agents` reads neither the providers' price table (contract 3) nor the features
    (`settings`, `memory`, `research`...: contract 6, D82).
    On exit: session tasks cancelled and awaited (status unchanged, resumed at the
    next startup), then the bus writes flushed, then the checkpointer closed, all of it before
    the caller closes the engine."""
    async with open_checkpointer(settings.checkpoints_path) as checkpointer:
        bus = EventBus(session_factory)
        runner = SessionRunner(
            session_factory=session_factory,
            bus=bus,
            models=models,
            checkpointer=checkpointer,
            prices=prices,
            run_settings=run_settings,
            ports=ports,
        )
        try:
            recovered = await runner.recover_on_startup()
            if recovered:
                logger.info("%d session(s) resumed after restart", len(recovered))
            yield AgentRuntime(bus=bus, runner=runner)
        finally:
            await runner.shutdown()
            await bus.aclose()
