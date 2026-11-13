"""Matériel des tests du parcours `capture` : runner sur le registre réel, faux modèles par agent
(`CouncilModels`, qui gardent chaque prompt), vraie recherche web (garde, cache, journal de
l'outil) sur un faux lecteur de pages, et faux port de la capture (`FakeCaptureStore`). Aucun
réseau ni LLM réel."""

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AsyncExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.nodes.archivist_capture_steps import CAPTURE_REQUEST
from app.agents.runtime.bus import EventBus
from app.agents.runtime.checkpointer import open_checkpointer
from app.agents.runtime.costs import ModelPrice
from app.agents.runtime.ports import AgentPorts
from app.agents.runtime.run_settings import RunSettings
from app.agents.runtime.runner import SessionRunner
from app.agents.tools.capture_port import CaptureMaterial
from app.core.errors import AppError
from app.db.models.agents import AgentSession
from app.features.research.service.gateway import AgentWebGateway
from app.providers.search.fake import FakeSearch
from app.providers.web.base import WebDocument
from tests.agents.graphs.council_models import CouncilModels
from tests.agents.graphs.web_support import add_users, research_runtime
from tests.agents.runtime.runner_helpers import TIMEOUT, all_events, get_session, wait_status
from tests.support.capture import FakeCaptureStore, digest_reply
from tests.support.memory import FakeWebReader

PAGE_URL = "https://blog.exemple.org/attention"
PAGE_TEXT = "Le mécanisme d'attention compare chaque mot aux autres mots de la phrase."


def page(text: str = PAGE_TEXT, title: str = "Comprendre l'attention") -> WebDocument:
    return WebDocument(PAGE_URL, title, text, "Ada Lovelace", "2026-01-02", "fr", None)


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
class CaptureRun:
    runner: SessionRunner
    factory: async_sessionmaker[AsyncSession]
    store: FakeCaptureStore
    reader: FakeWebReader
    models: CouncilModels
    user_id: str
    sid: str = ""
    pending: dict[str, Any] | None = None

    async def wait_status(self, status: str) -> AgentSession:
        return await wait_status(self.factory, self.user_id, self.sid, status)

    async def wait_question(self, kind: str) -> dict[str, Any]:
        """Attend une question `kind` nouvelle (pas celle déjà gardée dans `pending`)."""
        old = (self.pending or {}).get("interrupt_id")
        async with asyncio.timeout(TIMEOUT):
            while True:
                row = await get_session(self.factory, self.user_id, self.sid)
                pending = row.pending_interrupt or {}
                fresh = pending.get("interrupt_id") != old
                if row.status == "waiting_user" and pending.get("kind") == kind and fresh:
                    self.pending = pending
                    return pending
                assert row.status not in ("failed", "completed"), row.error
                await asyncio.sleep(0.01)

    async def resume(self, value: Any) -> None:
        row = await get_session(self.factory, self.user_id, self.sid)
        interrupt_id = (row.pending_interrupt or {}).get("interrupt_id")
        await self.runner.resume(self.user_id, self.sid, interrupt_id, value)

    async def events(self, type_: str) -> list[dict[str, Any]]:
        events = await all_events(self.factory, self.user_id, self.sid)
        return [e.payload.model_dump() for e in events if e.type == type_]

    async def types(self) -> list[str]:
        return [e.type for e in await all_events(self.factory, self.user_id, self.sid)]

    async def said(self) -> list[str]:
        return [e["text"] for e in await self.events("agent.message")]

    def prompts(self) -> list[str]:
        """Prompt de chaque appel de l'Archiviste, dans l'ordre (schéma JSON compris)."""
        return [c.prompt for c in self.models.calls if c.agent == "archivist"]


type MakeCapture = Callable[..., Awaitable[CaptureRun]]


def archivist(*replies: str) -> CouncilModels:
    """Faux modèles : l'Archiviste rend `replies`, puis `digest_reply()`."""
    models = CouncilModels()
    models.when("archivist", CAPTURE_REQUEST, *replies, *[digest_reply()] * 10)
    return models


@pytest.fixture
async def make_capture_runner(
    tmp_path: Path,
    db_session_factory: async_sessionmaker[AsyncSession],
    user_id: str,
    other_user_id: str,
) -> AsyncIterator[MakeCapture]:
    """`make(models, body=…)` lance `capture` (`pages` : ce que lit le faux lecteur, `documents` :
    les réponses successives du port, posées avant le départ) ; `sid=` reprend une session
    existante (nouveau « processus » : même base, même `checkpoints.db`, même port, même
    lecteur)."""
    await add_users(db_session_factory, user_id, other_user_id)
    store, reader = FakeCaptureStore(), FakeWebReader()
    web = AgentWebGateway(research_runtime(db_session_factory, FakeSearch("searxng"), reader))
    async with AsyncExitStack() as stack:

        async def make(
            models: CouncilModels | None = None,
            *,
            body: dict[str, Any] | None = None,
            sid: str | None = None,
            pages: dict[str, WebDocument | AppError] | None = None,
            documents: dict[str, list[CaptureMaterial | None]] | None = None,
        ) -> CaptureRun:
            models = models or archivist()
            reader.pages.update(pages or {})
            store.documents.update(documents or {})
            saver = await stack.enter_async_context(open_checkpointer(tmp_path / "checkpoints.db"))
            bus = EventBus(db_session_factory)
            runner = SessionRunner(
                session_factory=db_session_factory,
                bus=bus,
                models=models,
                checkpointer=saver,
                prices={"modele-test": ModelPrice(1.0, 2.0)},
                run_settings=_Settings(),
                ports=AgentPorts(web=web, capture=store),
            )
            stack.push_async_callback(bus.aclose)
            stack.push_async_callback(runner.shutdown)
            run = CaptureRun(runner, db_session_factory, store, reader, models, user_id)
            run.sid = sid or await runner.start(user_id, "capture", body or {"url": PAGE_URL})
            return run

        yield make
