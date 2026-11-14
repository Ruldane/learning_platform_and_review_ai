"""Matériel des tests du parcours `cv_capture` en mode `design` : runner sur le registre réel, faux
modèles par agent (`CouncilModels`, qui gardent chaque prompt, ici avec les messages) et faux port
des gabarits (`FakeCvTemplateStore`). Aucun réseau ni LLM réel."""

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from langchain_core.messages import BaseMessage
from langchain_core.messages.ai import UsageMetadata
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.nodes.designer import DRAFT_REQUEST, FIX_REQUEST, SAMPLE_REQUEST
from app.agents.runtime.bus import EventBus
from app.agents.runtime.checkpointer import open_checkpointer
from app.agents.runtime.costs import ModelPrice
from app.agents.runtime.ports import AgentPorts
from app.agents.runtime.run_settings import RunSettings
from app.agents.runtime.runner import SessionRunner
from app.db.models.agents import AgentSession
from tests.agents.graphs.council_models import CouncilModels
from tests.agents.graphs.web_support import add_users
from tests.agents.runtime.runner_helpers import TIMEOUT, all_events, get_session, wait_status
from tests.support.cv_templates import FakeCvTemplateStore, sample_reply, spec_reply

TEMPLATE_ID = "t1"


class _Settings:
    async def get_run_settings(self, user_id: str) -> RunSettings:
        return RunSettings(
            session_token_cap=1_000_000,
            debate_rounds=1,
            lesson_language="fr",
            search_languages=("fr",),
            style_guide="",
        )


@dataclass
class SpyModels(CouncilModels):
    """`CouncilModels` qui garde aussi les messages de chaque appel (blocs d'image compris)."""

    messages: list[list[BaseMessage]] = field(default_factory=list)

    def reply(self, agent: str, messages: list[BaseMessage]) -> tuple[int, str, UsageMetadata]:
        self.messages.append(list(messages))
        return super().reply(agent, messages)


def designer(
    *, sample: Sequence[str] = (), draft: Sequence[str] = (), fix: Sequence[str] = ()
) -> SpyModels:
    """Faux modèles : le Maquettiste rend d'abord les réponses du test, puis un contenu recopié
    et des descriptions valables."""
    models = SpyModels()
    models.when("designer", SAMPLE_REQUEST, *sample, *[sample_reply()] * 10)
    models.when("designer", DRAFT_REQUEST, *draft, *[spec_reply()] * 10)
    models.when("designer", FIX_REQUEST, *fix, *[spec_reply()] * 30)
    return models


@dataclass
class DesignRun:
    runner: SessionRunner
    factory: async_sessionmaker[AsyncSession]
    store: FakeCvTemplateStore
    models: SpyModels
    user_id: str
    sid: str = ""
    pending: dict[str, Any] | None = None

    async def wait_status(self, status: str) -> AgentSession:
        return await wait_status(self.factory, self.user_id, self.sid, status)

    async def question(self) -> dict[str, Any]:
        """Attend une question `cv_template` nouvelle (pas celle déjà gardée dans `pending`)."""
        old = (self.pending or {}).get("interrupt_id")
        async with asyncio.timeout(TIMEOUT):
            while True:
                row = await get_session(self.factory, self.user_id, self.sid)
                pending = row.pending_interrupt or {}
                fresh = pending.get("interrupt_id") != old
                if row.status == "waiting_user" and pending.get("kind") == "cv_template" and fresh:
                    self.pending = pending
                    return pending
                assert row.status not in ("failed", "completed"), row.error
                await asyncio.sleep(0.01)

    async def answer(self, value: Any) -> None:
        row = await get_session(self.factory, self.user_id, self.sid)
        interrupt_id = (row.pending_interrupt or {}).get("interrupt_id")
        await self.runner.resume(self.user_id, self.sid, interrupt_id, value)

    async def events(self, type_: str) -> list[dict[str, Any]]:
        events = await all_events(self.factory, self.user_id, self.sid)
        return [e.payload.model_dump() for e in events if e.type == type_]

    async def said(self) -> list[str]:
        return [e["text"] for e in await self.events("agent.message")]

    def prompts(self, marker: str = "") -> list[str]:
        """Prompt de chaque appel du Maquettiste (schéma JSON compris), dans l'ordre."""
        return [c.prompt for c in self.models.calls if c.agent == "designer" and marker in c.prompt]


type MakeDesign = Callable[..., Awaitable[DesignRun]]


@pytest.fixture
def design_store() -> FakeCvTemplateStore:
    return FakeCvTemplateStore()


@pytest.fixture
async def design_runner(
    tmp_path: Path,
    db_session_factory: async_sessionmaker[AsyncSession],
    user_id: str,
    other_user_id: str,
    design_store: FakeCvTemplateStore,
) -> AsyncIterator[MakeDesign]:
    """`make(models)` lance `cv_capture` (mode `design`, gabarit `t1`) sur le port
    `design_store` ; `sid=` reprend une session existante (nouveau « processus » : même base,
    même `checkpoints.db`, même port)."""
    await add_users(db_session_factory, user_id, other_user_id)
    async with AsyncExitStack() as stack:

        async def make(models: SpyModels | None = None, *, sid: str | None = None) -> DesignRun:
            models = models or designer()
            saver = await stack.enter_async_context(open_checkpointer(tmp_path / "checkpoints.db"))
            bus = EventBus(db_session_factory)
            runner = SessionRunner(
                session_factory=db_session_factory,
                bus=bus,
                models=models,
                checkpointer=saver,
                prices={"modele-test": ModelPrice(1.0, 2.0)},
                run_settings=_Settings(),
                ports=AgentPorts(cv_templates=design_store),
            )
            stack.push_async_callback(bus.aclose)
            stack.push_async_callback(runner.shutdown)
            run = DesignRun(runner, db_session_factory, design_store, models, user_id)
            body = {"mode": "design", "template_id": TEMPLATE_ID}
            run.sid = sid or await runner.start(user_id, "cv_capture", body)
            return run

        yield make
