"""Matériel des tests du parcours `replan` : runner sur le registre réel, faux modèles par agent
(`CouncilModels`, qui gardent chaque prompt) et faux port de la replanification
(`FakeReplanStore`). Aucun réseau ni LLM réel."""

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AsyncExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.nodes.strategist.replan_steps import REPLAN_REQUEST
from app.agents.runtime.bus import EventBus
from app.agents.runtime.checkpointer import open_checkpointer
from app.agents.runtime.costs import ModelPrice
from app.agents.runtime.ports import AgentPorts
from app.agents.runtime.run_settings import RunSettings
from app.agents.runtime.runner import SessionRunner
from app.agents.tools.replan_port import ReplanContext
from app.db.models.agents import AgentSession
from tests.agents.graphs.council_models import CouncilModels
from tests.agents.graphs.web_support import add_users
from tests.agents.runtime.runner_helpers import TIMEOUT, all_events, get_session, wait_status
from tests.support.replan import PROGRAM_ID, REVIEW_ID, FakeReplanStore, replan_context

SUMMARY = "Le plan est rangé dans ton budget, retards compris."
WEEKLY = {"program_id": PROGRAM_ID, "trigger": "weekly_review", "review_entry_id": REVIEW_ID}


def reply(summary: str = SUMMARY, **over: Any) -> str:
    return json.dumps({"summary": summary} | over)


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
class ReplanRun:
    runner: SessionRunner
    factory: async_sessionmaker[AsyncSession]
    store: FakeReplanStore
    models: CouncilModels
    user_id: str
    sid: str = ""
    pending: dict[str, Any] | None = None

    async def wait_status(self, status: str) -> AgentSession:
        return await wait_status(self.factory, self.user_id, self.sid, status)

    async def wait_question(self, kind: str = "accept_replan") -> dict[str, Any]:
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

    async def kinds(self) -> list[str]:
        return [e["kind"] for e in await self.events("interrupt.requested")]

    async def said(self) -> list[str]:
        return [e["text"] for e in await self.events("agent.message")]

    def prompts(self) -> list[str]:
        """Prompt de chaque appel du Stratège, dans l'ordre (schéma JSON compris)."""
        return [c.prompt for c in self.models.calls if c.agent == "strategist"]


type MakeReplan = Callable[..., Awaitable[ReplanRun]]


@pytest.fixture
async def make_replan_runner(
    tmp_path: Path,
    db_session_factory: async_sessionmaker[AsyncSession],
    user_id: str,
    other_user_id: str,
) -> AsyncIterator[MakeReplan]:
    """`make(models, plan=…, body=…)` lance `replan` sur le plan du faux port (bilan « dans les
    temps » par défaut) ; le Stratège rend `reply()` après les règles du test. `sid=` reprend une
    session existante (nouveau « processus » : même base, même `checkpoints.db`, même port)."""
    await add_users(db_session_factory, user_id, other_user_id)
    store = FakeReplanStore()
    async with AsyncExitStack() as stack:

        async def make(
            models: CouncilModels | None = None,
            *,
            plan: ReplanContext | None = None,
            body: dict[str, Any] | None = None,
            sid: str | None = None,
            prepare: Callable[[FakeReplanStore], None] | None = None,
        ) -> ReplanRun:
            models = models or CouncilModels()
            models.when("strategist", REPLAN_REQUEST, *[reply()] * 20)  # après celles du test
            if sid is None or plan is not None:
                store.add(user_id, plan or replan_context())
            if prepare is not None:
                prepare(store)
            saver = await stack.enter_async_context(open_checkpointer(tmp_path / "checkpoints.db"))
            bus = EventBus(db_session_factory)
            runner = SessionRunner(
                session_factory=db_session_factory,
                bus=bus,
                models=models,
                checkpointer=saver,
                prices={"modele-test": ModelPrice(1.0, 2.0)},
                run_settings=_Settings(),
                ports=AgentPorts(replan=store),
            )
            stack.push_async_callback(bus.aclose)
            stack.push_async_callback(runner.shutdown)
            run = ReplanRun(runner, db_session_factory, store, models, user_id)
            run.sid = sid or await runner.start(user_id, "replan", body or WEEKLY)
            return run

        yield make
