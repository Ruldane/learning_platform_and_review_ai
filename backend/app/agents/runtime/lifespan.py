"""Le moteur d'agents dans la vie de l'application : checkpointer, bus et runner ouverts au
démarrage (avec reprise des sessions interrompues), fermés dans l'ordre à l'arrêt."""

import logging
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.bus import EventBus
from app.agents.runtime.checkpointer import open_checkpointer
from app.agents.runtime.costs import ModelPrice
from app.agents.runtime.deps import ChatModelSource
from app.agents.runtime.handle import AgentRuntime
from app.agents.runtime.run_settings import RunSettingsSource
from app.agents.runtime.runner import SessionRunner
from app.agents.tools.memory_port import NO_MEMORY, MemoryGateway
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
    memory: MemoryGateway = NO_MEMORY,
) -> AsyncIterator[AgentRuntime]:
    """`prices`, `run_settings` et `memory` viennent de la composition (`app.bootstrap`) :
    `app.agents` ne lit ni la table des prix des fournisseurs (contrat 3) ni les features
    `settings` et `memory` (contrat 6).
    À la sortie : tâches des sessions annulées et attendues (statut inchangé, reprises au
    prochain démarrage), puis écritures du bus vidées, puis checkpointer fermé — le tout avant
    la fermeture du moteur par l'appelant."""
    async with open_checkpointer(settings.checkpoints_path) as checkpointer:
        bus = EventBus(session_factory)
        runner = SessionRunner(
            session_factory=session_factory,
            bus=bus,
            models=models,
            checkpointer=checkpointer,
            prices=prices,
            run_settings=run_settings,
            memory=memory,
        )
        try:
            recovered = await runner.recover_on_startup()
            if recovered:
                logger.info("%d session(s) reprise(s) après redémarrage", len(recovered))
            yield AgentRuntime(bus=bus, runner=runner)
        finally:
            await runner.shutdown()
            await bus.aclose()
