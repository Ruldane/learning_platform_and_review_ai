"""Matériel des tests du parcours `interview` : runner sur le registre réel, faux modèle de
l'Intervieweur (`CouncilModels`, qui garde chaque prompt) et faux port des entretiens
(`FakeInterviewStore`). Aucun réseau ni LLM réel."""

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AsyncExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.nodes.interviewer.debrief import DEBRIEF_REQUEST
from app.agents.nodes.interviewer.plan import PLAN_REQUEST
from app.agents.nodes.interviewer.turn import TURN_REQUEST
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
from tests.support.interviews import INTERVIEW_ID, FakeInterviewStore

KIND = "interview_answer"
CRITERIA = ["clarity", "structure", "technical_depth", "role_fit"]
SOURCES = ["posting", "company_dossier", "cv", "gap", "general"]


def question_text(rank: int) -> str:
    return f"Question numéro {rank} sur le poste ?"


def plan_json(count: int = 4) -> str:
    questions = [
        {
            "text": question_text(rank),
            "criterion": CRITERIA[rank % 4],
            "source": SOURCES[rank % 5],
        }
        for rank in range(1, count + 1)
    ]
    return json.dumps({"questions": questions}, ensure_ascii=False)


def turn_json(note: int = 4, follow_up: str | None = None) -> str:
    return json.dumps({"follow_up": follow_up, "note": note}, ensure_ascii=False)


def debrief_json(**over: Any) -> str:
    data: dict[str, Any] = {
        "scores": {"clarity": 4, "structure": 3, "technical_depth": 2, "role_fit": 4},
        "strengths": ["Réponses claires", "Bon ancrage dans le poste", "Exemples concrets"],
        "fixes": ["Structurer avec situation et résultat", "Plus de précision", "Conclure"],
        "weakest_index": 0,
        "improved_answer": "J'ai conçu un assistant et je l'ai mis en production avec soin.",
        "missed": [],
        "expected": [],
    }
    return json.dumps(data | over, ensure_ascii=False)


def expected(*indices: int) -> list[dict[str, Any]]:
    return [{"index": i, "points": [f"Point clé {i} a", f"Point clé {i} b"]} for i in indices]


def interviewer(
    *,
    plans: list[str] | None = None,
    turns: list[str] | None = None,
    debriefs: list[str] | None = None,
) -> CouncilModels:
    """Faux modèles : les réponses du test d'abord (plan, tours, débrief), puis les réponses
    valables (un plan de quatre questions, une note de 4, un débrief sans fiche)."""
    models = CouncilModels()
    models.when("interviewer", PLAN_REQUEST, *(plans or []), *[plan_json()] * 3)
    models.when("interviewer", TURN_REQUEST, *(turns or []), *[turn_json()] * 30)
    models.when("interviewer", DEBRIEF_REQUEST, *(debriefs or []), *[debrief_json()] * 5)
    return models


def answer(text: str = "Ma réponse détaillée.") -> dict[str, Any]:
    return {"answers": {"answer": text}}


def prompts(models: CouncilModels, request: str) -> list[str]:
    return [c.prompt for c in models.calls if c.agent == "interviewer" and request in c.prompt]


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
class InterviewRun:
    runner: SessionRunner
    factory: async_sessionmaker[AsyncSession]
    store: FakeInterviewStore
    models: CouncilModels
    user_id: str
    sid: str = ""
    pending: dict[str, Any] | None = None

    async def wait_status(self, status: str) -> AgentSession:
        return await wait_status(self.factory, self.user_id, self.sid, status)

    async def question(self) -> dict[str, Any]:
        """Attend une question `interview_answer` nouvelle (pas celle déjà gardée)."""
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

    async def answer_all(self, count: int) -> list[str]:
        """Répond à `count` questions (principales ou relances) ; rend les textes posés."""
        asked = []
        for _ in range(count):
            asked.append((await self.question())["question"])
            await self.answer(answer())
        return asked

    async def events(self, type_: str) -> list[dict[str, Any]]:
        events = await all_events(self.factory, self.user_id, self.sid)
        return [e.payload.model_dump() for e in events if e.type == type_]


type MakeInterview = Callable[..., Awaitable[InterviewRun]]


@pytest.fixture
def interview_store() -> FakeInterviewStore:
    return FakeInterviewStore()


@pytest.fixture
async def interview_runner(
    tmp_path: Path,
    db_session_factory: async_sessionmaker[AsyncSession],
    user_id: str,
    other_user_id: str,
    interview_store: FakeInterviewStore,
) -> AsyncIterator[MakeInterview]:
    """`make(models)` lance `interview` ; `sid=` reprend une session existante (nouveau
    « processus » : même base, même `checkpoints.db`, même port)."""
    await add_users(db_session_factory, user_id, other_user_id)
    async with AsyncExitStack() as stack:

        async def make(
            models: CouncilModels | None = None, *, sid: str | None = None
        ) -> InterviewRun:
            models = models or interviewer()
            saver = await stack.enter_async_context(open_checkpointer(tmp_path / "checkpoints.db"))
            bus = EventBus(db_session_factory)
            runner = SessionRunner(
                session_factory=db_session_factory,
                bus=bus,
                models=models,
                checkpointer=saver,
                prices={"modele-test": ModelPrice(1.0, 2.0)},
                run_settings=_Settings(),
                ports=AgentPorts(interviews=interview_store),
            )
            stack.push_async_callback(bus.aclose)
            stack.push_async_callback(runner.shutdown)
            run = InterviewRun(runner, db_session_factory, interview_store, models, user_id)
            run.sid = sid or await runner.start(
                user_id, "interview", {"interview_id": INTERVIEW_ID}
            )
            return run

        yield make
