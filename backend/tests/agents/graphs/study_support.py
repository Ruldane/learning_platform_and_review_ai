"""Matériel des tests du parcours `study_session` : runner sur le registre réel, faux modèles par
agent (`CouncilModels`, qui gardent chaque prompt), faux port des sessions d'étude
(`FakeStudyStore`) et mémoire factice. Aucun réseau ni LLM réel."""

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AsyncExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.nodes.tutor.answers import CHECK_REQUEST, HINT_REQUEST
from app.agents.nodes.tutor.teach import FINAL_REQUEST, REPLY_REQUEST, TEACH_REQUEST
from app.agents.nodes.tutor.wrap import SUMMARY_REQUEST
from app.agents.runtime.bus import EventBus
from app.agents.runtime.checkpointer import open_checkpointer
from app.agents.runtime.costs import ModelPrice
from app.agents.runtime.ports import AgentPorts
from app.agents.runtime.run_settings import RunSettings
from app.agents.runtime.runner import SessionRunner
from app.agents.tools.memory_port import MemoryGateway
from app.db.models.agents import AgentSession
from tests.agents.graphs.council_models import CouncilModels
from tests.agents.graphs.web_support import add_users
from tests.agents.runtime.runner_helpers import TIMEOUT, all_events, get_session, wait_status
from tests.support.study import STUDY_ID, FakeStudyMemory, FakeStudyStore


def teach_turn(question: str = "Que fait la softmax des scores ?", **over: Any) -> str:
    turn = {
        "message": "La softmax change des scores en poids [1].",
        "question": question,
        "expected": "Des poids positifs qui somment à 1.",
        "mermaid": None,
    }
    return json.dumps(turn | over)


def check(verdict: str = "correct", feedback: str = "C'est juste [1].") -> str:
    return json.dumps({"verdict": verdict, "feedback": feedback})


def hint(text: str = "Pense aux exponentielles.") -> str:
    return json.dumps({"hint": text})


FINALS = json.dumps(
    {
        "questions": [
            {"question": f"Question finale numéro {n} ?", "expected": f"Attendu {n}."}
            for n in (1, 2, 3)
        ]
    }
)
SUMMARY = json.dumps({"summary": "Bonne séance : la softmax est acquise."})
REPLY = json.dumps({"message": "Bonne question : la softmax normalise [2]."})
DEFAULTS = [
    (TEACH_REQUEST, teach_turn()),
    (CHECK_REQUEST, check()),
    (HINT_REQUEST, hint()),
    (FINAL_REQUEST, FINALS),
    (SUMMARY_REQUEST, SUMMARY),
    (REPLY_REQUEST, REPLY),
]


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
class StudyRun:
    runner: SessionRunner
    factory: async_sessionmaker[AsyncSession]
    store: FakeStudyStore
    models: CouncilModels
    user_id: str
    sid: str = ""
    pending: dict[str, Any] | None = None

    async def wait_status(self, status: str) -> AgentSession:
        return await wait_status(self.factory, self.user_id, self.sid, status)

    async def wait_question(self, kind: str = "tutor_question") -> dict[str, Any]:
        """Attend une question `kind` nouvelle (pas celle déjà gardée dans `pending`)."""
        old = (self.pending or {}).get("interrupt_id")
        async with asyncio.timeout(TIMEOUT * 4):
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

    async def answer(self, text: str) -> None:
        await self.resume({"answers": {"answer": text}})

    async def post_message(self, text: str) -> None:
        await self.runner.post_message(self.user_id, self.sid, text)

    async def events(self, type_: str) -> list[dict[str, Any]]:
        events = await all_events(self.factory, self.user_id, self.sid)
        return [e.payload.model_dump() for e in events if e.type == type_]

    async def kinds(self) -> list[str]:
        return [e["kind"] for e in await self.events("interrupt.requested")]

    async def answer_all(self, count: int, text: str = "Ma réponse détaillée.") -> None:
        """Répond `count` fois de suite à la question du Tuteur."""
        for _ in range(count):
            await self.wait_question()
            await self.answer(text)

    def prompts(self, marker: str = "") -> list[str]:
        """Prompt de chaque appel du Tuteur (dont la demande contient `marker`), dans l'ordre."""
        return [c.prompt for c in self.models.calls if c.agent == "tutor" and marker in c.prompt]


type MakeStudy = Callable[..., Awaitable[StudyRun]]


@pytest.fixture
async def study_store() -> FakeStudyStore:
    return FakeStudyStore()


@pytest.fixture
async def make_study_runner(
    tmp_path: Path,
    db_session_factory: async_sessionmaker[AsyncSession],
    user_id: str,
    other_user_id: str,
    study_store: FakeStudyStore,
) -> AsyncIterator[MakeStudy]:
    """`make(models)` lance `study_session` sur la séance du faux port (à ajouter avant, sinon
    celle par défaut). Le Tuteur rend les réponses `DEFAULTS` après les règles du test.
    `start=False` : pas de départ ; `sid=` reprend une session existante (nouveau « processus » :
    même base, même `checkpoints.db`, même port) ; `memory=` : la mémoire vue par le Tuteur."""
    await add_users(db_session_factory, user_id, other_user_id)
    if (user_id, STUDY_ID) not in study_store.contexts:
        study_store.add(user_id)
    async with AsyncExitStack() as stack:

        async def make(
            models: CouncilModels | None = None,
            *,
            sid: str | None = None,
            start: bool = True,
            memory: MemoryGateway | None = None,
        ) -> StudyRun:
            models = models or CouncilModels()
            for marker, reply in DEFAULTS:
                models.when("tutor", marker, *[reply] * 30)  # après celles du test
            saver = await stack.enter_async_context(open_checkpointer(tmp_path / "checkpoints.db"))
            bus = EventBus(db_session_factory)
            runner = SessionRunner(
                session_factory=db_session_factory,
                bus=bus,
                models=models,
                checkpointer=saver,
                prices={"modele-test": ModelPrice(1.0, 2.0)},
                run_settings=_Settings(),
                ports=AgentPorts(study=study_store, memory=memory or FakeStudyMemory()),
            )
            stack.push_async_callback(bus.aclose)
            stack.push_async_callback(runner.shutdown)
            run = StudyRun(runner, db_session_factory, study_store, models, user_id)
            if sid is not None:
                run.sid = sid
            elif start:
                body = {"study_session_id": STUDY_ID}
                run.sid = await runner.start(user_id, "study_session", body)
            return run

        yield make
