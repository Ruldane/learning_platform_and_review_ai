"""Matériel des tests du parcours `program_builder` : runner sur le registre réel, faux modèles par
agent (`CouncilModels`) et faux port du programme (`FakeProgramStore`, sur les vraies règles de
4.2). Aucun réseau ni LLM réel."""

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AsyncExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.nodes.strategist.plan import PLAN_REQUEST
from app.agents.runtime.bus import EventBus
from app.agents.runtime.checkpointer import open_checkpointer
from app.agents.runtime.costs import ModelPrice
from app.agents.runtime.ports import AgentPorts
from app.agents.runtime.run_settings import RunSettings
from app.agents.runtime.runner import SessionRunner
from app.agents.tools.council_port import ProposalDraft
from app.db.models.agents import AgentSession
from tests.agents.graphs.council_models import CouncilModels, proposal
from tests.agents.graphs.web_support import add_users
from tests.agents.runtime.runner_helpers import TIMEOUT, all_events, get_session, wait_status
from tests.support.council import GOAL_ID
from tests.support.program import FakeProgramStore, full_week, plan

# Semaine 1 à 485 min (au moins 60 % du plafond de 714, D98), la dernière libre.
GOOD_PLAN = plan(
    [full_week("Bases", [120, 120, 120, 60]), full_week("Projet", [90])]
).model_dump_json()
START = "2026-11-16"


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
class Builder:
    runner: SessionRunner
    factory: async_sessionmaker[AsyncSession]
    store: FakeProgramStore
    models: CouncilModels
    user_id: str
    proposal_ids: list[str]
    sid: str = ""
    pending: dict[str, Any] | None = None

    async def wait_status(self, status: str) -> AgentSession:
        return await wait_status(self.factory, self.user_id, self.sid, status)

    async def wait_question(self, *, after: dict[str, Any] | None = None) -> dict[str, Any]:
        """Attend la question `validate_program` (une nouvelle si `after`), gardée dans
        `pending`."""
        old = (after or {}).get("interrupt_id")
        async with asyncio.timeout(TIMEOUT):
            while True:
                row = await get_session(self.factory, self.user_id, self.sid)
                pending = row.pending_interrupt or {}
                fresh = pending.get("interrupt_id") != old
                if row.status == "waiting_user" and fresh:
                    assert pending.get("kind") == "validate_program"
                    self.pending = pending
                    return pending
                assert row.status not in ("failed", "completed"), row.error
                await asyncio.sleep(0.01)

    async def resume(self, value: Any) -> None:
        row = await get_session(self.factory, self.user_id, self.sid)
        pending = row.pending_interrupt or {}
        await self.runner.resume(self.user_id, self.sid, pending.get("interrupt_id"), value)

    async def events(self, type_: str) -> list[dict[str, Any]]:
        events = await all_events(self.factory, self.user_id, self.sid)
        return [e.payload.model_dump() for e in events if e.type == type_]

    def plan_prompts(self) -> list[str]:
        """Prompt de chaque appel du Stratège, dans l'ordre."""
        return [call.prompt for call in self.models.calls if call.agent == "strategist"]

    def prompt_of_call(self, number: int) -> str:
        """Prompt du `number`-ième appel du Stratège (à partir de 1)."""
        return self.plan_prompts()[number - 1]

    def prompt_of_last_plan(self) -> str:
        return self.plan_prompts()[-1]


type MakeBuilder = Callable[..., Awaitable[Builder]]


@pytest.fixture
async def make_builder_runner(
    tmp_path: Path,
    db_session_factory: async_sessionmaker[AsyncSession],
    user_id: str,
    other_user_id: str,
) -> AsyncIterator[MakeBuilder]:
    """`make(models)` lance `program_builder` sur l'objectif du faux port et sa première
    proposition (`mix=True` : les deux) ; `prepare` règle le port avant le départ. Le Stratège
    rend `GOOD_PLAN` par défaut, après les règles du test. `sid=` reprend une session existante
    (nouveau « processus » : même base, même `checkpoints.db`, même port)."""
    await add_users(db_session_factory, user_id, other_user_id)
    store = FakeProgramStore()
    drafts = [ProposalDraft.model_validate(proposal(n)) for n in ("Parcours pratique", "Socle")]
    ids = store.add_goal(user_id, drafts)
    async with AsyncExitStack() as stack:

        async def make(
            models: CouncilModels | None = None,
            *,
            sid: str | None = None,
            mix: bool = False,
            prepare: Callable[[FakeProgramStore], None] | None = None,
        ) -> Builder:
            models = models or CouncilModels()
            models.when("strategist", PLAN_REQUEST, *[GOOD_PLAN] * 20)  # après celles du test
            saver = await stack.enter_async_context(open_checkpointer(tmp_path / "checkpoints.db"))
            bus = EventBus(db_session_factory)
            runner = SessionRunner(
                session_factory=db_session_factory,
                bus=bus,
                models=models,
                checkpointer=saver,
                prices={"modele-test": ModelPrice(1.0, 2.0)},
                run_settings=_Settings(),
                ports=AgentPorts(program=store),
            )
            stack.push_async_callback(bus.aclose)
            stack.push_async_callback(runner.shutdown)
            builder = Builder(runner, db_session_factory, store, models, user_id, ids)
            if prepare is not None:
                prepare(store)
            chosen = ids if mix else ids[:1]
            body = {"goal_id": GOAL_ID, "proposal_ids": chosen, "start_date": START}
            builder.sid = sid or await runner.start(user_id, "program_builder", body)
            return builder

        yield make
