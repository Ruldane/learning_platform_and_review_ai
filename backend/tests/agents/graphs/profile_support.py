"""Matériel des tests du parcours `cv_capture` en mode `profile` : runner sur le registre réel,
faux modèles par agent (`CouncilModels`, qui gardent chaque prompt) et faux port du profil
(`FakeProfileStore`). Aucun réseau ni LLM réel."""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AsyncExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.graphs.cv_capture import PROFILE_REQUEST
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
from tests.support.profile import FakeProfileStore, profile_reply


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
class ProfileRun:
    runner: SessionRunner
    factory: async_sessionmaker[AsyncSession]
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
        """Prompt de chaque appel de l'Archiviste (schéma JSON compris), dans l'ordre."""
        return [
            c.prompt for c in self.models.calls if c.agent == "archivist" and marker in c.prompt
        ]


type MakeProfile = Callable[..., Awaitable[ProfileRun]]


def archivist(*replies: str) -> CouncilModels:
    """Faux modèles : l'Archiviste rend `replies`, puis le profil du CV fictif."""
    models = CouncilModels()
    models.when("archivist", PROFILE_REQUEST, *replies, *[profile_reply()] * 10)
    return models


@pytest.fixture
def profile_store() -> FakeProfileStore:
    return FakeProfileStore()


@pytest.fixture
async def profile_runner(
    tmp_path: Path,
    db_session_factory: async_sessionmaker[AsyncSession],
    user_id: str,
    other_user_id: str,
    profile_store: FakeProfileStore,
) -> AsyncIterator[MakeProfile]:
    """`make(models, document_ids=…, note=…)` lance `cv_capture` (mode `profile`) avec le port
    `profile_store` ; `sid=` reprend une session existante (nouveau « processus » : même base,
    même `checkpoints.db`, même port)."""
    await add_users(db_session_factory, user_id, other_user_id)
    async with AsyncExitStack() as stack:

        async def make(
            models: CouncilModels | None = None,
            *,
            document_ids: list[str] | None = None,
            note: str | None = None,
            sid: str | None = None,
        ) -> ProfileRun:
            models = models or archivist()
            saver = await stack.enter_async_context(open_checkpointer(tmp_path / "checkpoints.db"))
            bus = EventBus(db_session_factory)
            runner = SessionRunner(
                session_factory=db_session_factory,
                bus=bus,
                models=models,
                checkpointer=saver,
                prices={"modele-test": ModelPrice(1.0, 2.0)},
                run_settings=_Settings(),
                ports=AgentPorts(profile=profile_store),
            )
            stack.push_async_callback(bus.aclose)
            stack.push_async_callback(runner.shutdown)
            run = ProfileRun(runner, db_session_factory, models, user_id)
            body = {"mode": "profile", "document_ids": document_ids or ["d1"], "note": note}
            run.sid = sid or await runner.start(user_id, "cv_capture", body)
            return run

        yield make
