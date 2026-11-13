"""Matériel des tests du parcours `gap_analysis` : runner sur le registre réel, faux modèles par
agent (`CouncilModels`, qui gardent chaque prompt) et faux port de l'analyse (`FakeGapStore`).
Aucun réseau ni LLM réel."""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AsyncExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.nodes.analyst_steps import ANALYZE_REQUEST, MATCH_REQUEST
from app.agents.runtime.bus import EventBus
from app.agents.runtime.checkpointer import open_checkpointer
from app.agents.runtime.costs import ModelPrice
from app.agents.runtime.ports import AgentPorts
from app.agents.runtime.run_settings import RunSettings
from app.agents.runtime.runner import SessionRunner
from app.db.models.agents import AgentSession
from tests.agents.graphs.council_models import CouncilModels
from tests.agents.graphs.web_support import add_users
from tests.agents.runtime.runner_helpers import all_events, wait_status
from tests.support.gap import POSTING_ID, FakeGapStore, analysis_reply, matches_reply


class _Settings:
    async def get_run_settings(self, user_id: str) -> RunSettings:
        return RunSettings(
            session_token_cap=300_000,
            debate_rounds=1,
            lesson_language="fr",
            search_languages=("fr",),
            style_guide="",
        )


@dataclass
class GapRun:
    runner: SessionRunner
    factory: async_sessionmaker[AsyncSession]
    store: FakeGapStore
    models: CouncilModels
    user_id: str
    sid: str = ""

    async def wait_status(self, status: str) -> AgentSession:
        return await wait_status(self.factory, self.user_id, self.sid, status)

    async def events(self, type_: str) -> list[dict[str, Any]]:
        events = await all_events(self.factory, self.user_id, self.sid)
        return [e.payload.model_dump() for e in events if e.type == type_]

    async def said(self) -> list[str]:
        return [e["text"] for e in await self.events("agent.message")]

    def prompts(self, marker: str = "") -> list[str]:
        """Prompt de chaque appel de l'Analyste (schéma JSON compris), dans l'ordre ; `marker` :
        seulement les appels dont le prompt le contient (`ANALYZE_REQUEST`, `MATCH_REQUEST`)."""
        return [c.prompt for c in self.models.calls if c.agent == "analyst" and marker in c.prompt]


type MakeGap = Callable[..., Awaitable[GapRun]]


def analyst(analyses: list[str] | None = None, matches: list[str] | None = None) -> CouncilModels:
    """Faux modèles : l'Analyste rend `analyses` (puis l'analyse de l'offre fictive) en mode
    `analyze`, et `matches` (puis les rattachements attendus) en mode `match`."""
    models = CouncilModels()
    models.when("analyst", ANALYZE_REQUEST, *(analyses or []), *[analysis_reply()] * 10)
    models.when("analyst", MATCH_REQUEST, *(matches or []), *[matches_reply()] * 10)
    return models


@pytest.fixture
def gap_store() -> FakeGapStore:
    return FakeGapStore()


@pytest.fixture
async def gap_runner(
    tmp_path: Path,
    db_session_factory: async_sessionmaker[AsyncSession],
    user_id: str,
    other_user_id: str,
    gap_store: FakeGapStore,
) -> AsyncIterator[MakeGap]:
    """`make(models)` lance `gap_analysis` sur l'offre fictive avec le port `gap_store` (à
    préparer avant) ; `sid=` reprend une session existante (nouveau « processus » : même base,
    même `checkpoints.db`, même port)."""
    await add_users(db_session_factory, user_id, other_user_id)
    store = gap_store
    async with AsyncExitStack() as stack:

        async def make(
            models: CouncilModels | None = None,
            *,
            posting_id: str = POSTING_ID,
            sid: str | None = None,
        ) -> GapRun:
            models = models or analyst()
            saver = await stack.enter_async_context(open_checkpointer(tmp_path / "checkpoints.db"))
            bus = EventBus(db_session_factory)
            runner = SessionRunner(
                session_factory=db_session_factory,
                bus=bus,
                models=models,
                checkpointer=saver,
                prices={"modele-test": ModelPrice(1.0, 2.0)},
                run_settings=_Settings(),
                ports=AgentPorts(gap=store),
            )
            stack.push_async_callback(bus.aclose)
            stack.push_async_callback(runner.shutdown)
            run = GapRun(runner, db_session_factory, store, models, user_id)
            body = {"posting_id": posting_id}
            run.sid = sid or await runner.start(user_id, "gap_analysis", body)
            return run

        yield make
