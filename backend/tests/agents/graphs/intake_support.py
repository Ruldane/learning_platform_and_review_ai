"""Matériel des tests du parcours `application_intake` : runner sur le registre réel, faux modèle
de l'Assistant de suivi (`CouncilModels`, qui garde chaque prompt) et faux port des candidatures
(`FakeApplicationStore`). Aucun réseau ni LLM réel."""

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AsyncExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.nodes.tracker.intake import INTAKE_REQUEST
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
from tests.support.applications import FakeApplicationStore

SENTENCE = "j'ai postulé hier chez Société Fictive pour le poste Développeuse IA"
KIND = "application_confirm"


def draft_json(**over: Any) -> str:
    """La réponse de l'Assistant de suivi : la fiche de `SENTENCE` (15 novembre 2026)."""
    fields: dict[str, Any] = {
        "company": "Société Fictive",
        "title": "Développeuse IA",
        "status": "applied",
        "applied_on": "2026-11-14",
        "channel": None,
        "contact_name": None,
        "contact_role": None,
        "notes": None,
    } | over
    return json.dumps(fields, ensure_ascii=False)


def tracker(*replies: str) -> CouncilModels:
    """Faux modèles : l'Assistant de suivi rend `replies`, puis la fiche de `SENTENCE`."""
    models = CouncilModels()
    models.when("tracker", INTAKE_REQUEST, *replies, *[draft_json()] * 5)
    return models


def field_values(question: dict[str, Any]) -> dict[str, str]:
    """Les champs de la question, tels que le front les renverra : `{id: valeur}`."""
    return {f["id"]: f.get("value") or "" for f in question["fields"]}


def tracker_prompts(models: CouncilModels) -> list[str]:
    return [c.prompt for c in models.calls if c.agent == "tracker"]


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
class IntakeRun:
    runner: SessionRunner
    factory: async_sessionmaker[AsyncSession]
    store: FakeApplicationStore
    models: CouncilModels
    user_id: str
    sid: str = ""
    pending: dict[str, Any] | None = None

    async def wait_status(self, status: str) -> AgentSession:
        return await wait_status(self.factory, self.user_id, self.sid, status)

    async def question(self) -> dict[str, Any]:
        """Attend une question `application_confirm` nouvelle (pas celle déjà gardée)."""
        old = (self.pending or {}).get("interrupt_id")
        async with asyncio.timeout(TIMEOUT):
            while True:
                row = await get_session(self.factory, self.user_id, self.sid)
                pending = row.pending_interrupt or {}
                fresh = pending.get("interrupt_id") != old
                if row.status == "waiting_user" and pending.get("kind") == KIND and fresh:
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


type MakeIntake = Callable[..., Awaitable[IntakeRun]]


@pytest.fixture
def intake_store() -> FakeApplicationStore:
    return FakeApplicationStore()


@pytest.fixture
async def intake_runner(
    tmp_path: Path,
    db_session_factory: async_sessionmaker[AsyncSession],
    user_id: str,
    other_user_id: str,
    intake_store: FakeApplicationStore,
) -> AsyncIterator[MakeIntake]:
    """`make(models, text=…)` lance `application_intake` ; `sid=` reprend une session existante
    (nouveau « processus » : même base, même `checkpoints.db`, même port)."""
    await add_users(db_session_factory, user_id, other_user_id)
    async with AsyncExitStack() as stack:

        async def make(
            models: CouncilModels | None = None, *, text: str = SENTENCE, sid: str | None = None
        ) -> IntakeRun:
            models = models or tracker()
            saver = await stack.enter_async_context(open_checkpointer(tmp_path / "checkpoints.db"))
            bus = EventBus(db_session_factory)
            runner = SessionRunner(
                session_factory=db_session_factory,
                bus=bus,
                models=models,
                checkpointer=saver,
                prices={"modele-test": ModelPrice(1.0, 2.0)},
                run_settings=_Settings(),
                ports=AgentPorts(applications=intake_store),
            )
            stack.push_async_callback(bus.aclose)
            stack.push_async_callback(runner.shutdown)
            run = IntakeRun(runner, db_session_factory, intake_store, models, user_id)
            run.sid = sid or await runner.start(user_id, "application_intake", {"text": text})
            return run

        yield make
