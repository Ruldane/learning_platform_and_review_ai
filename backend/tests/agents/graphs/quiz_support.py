"""Matériel des tests du parcours `quiz` : runner sur le registre réel, faux modèles par agent
(`CouncilModels`, qui gardent chaque prompt) et faux port des quiz (`FakeQuizStore`). Aucun réseau
ni LLM réel."""

import json
import re
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AsyncExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.nodes.examiner import GRADE_REQUEST, WRITE_REQUEST
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
from tests.support.quiz import ATTEMPT_ID, QUIZ_ID, FakeQuizStore, quiz_draft

GOOD_QUIZ = json.dumps(quiz_draft())
BODIES = {
    "generate": {"mode": "generate", "quiz_id": QUIZ_ID},
    "grade": {"mode": "grade", "attempt_id": ATTEMPT_ID},
}
_BLOCK = re.compile(
    r'<<<CONTENU_NON_FIABLE source="([^"]*)">>>\n(.*?)\n<<<FIN_CONTENU_NON_FIABLE>>>', re.DOTALL
)


def grades(*items: tuple[str, float, str]) -> str:
    return json.dumps({"items": [{"ref": r, "score": s, "feedback": f} for r, s, f in items]})


GOOD_GRADES = grades(
    ("q2", 1, "Réponse juste."), ("q3", 0.5, "Lecture partielle."), ("q4", 0, "Hors sujet.")
)


def between_untrusted_markers(prompt: str, label: str | None = None) -> str:
    """Le texte de chaque encadré non fiable du prompt (de la source `label` seulement si
    donnée), mis bout à bout."""
    return "\n".join(text for source, text in _BLOCK.findall(prompt) if label in (None, source))


def outside_untrusted_markers(prompt: str) -> str:
    return _BLOCK.sub("", prompt)


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
class QuizRun:
    runner: SessionRunner
    factory: async_sessionmaker[AsyncSession]
    store: FakeQuizStore
    models: CouncilModels
    user_id: str
    sid: str = ""

    async def wait_status(self, status: str) -> AgentSession:
        return await wait_status(self.factory, self.user_id, self.sid, status)

    async def events(self, type_: str) -> list[dict[str, Any]]:
        events = await all_events(self.factory, self.user_id, self.sid)
        return [e.payload.model_dump() for e in events if e.type == type_]

    def prompts(self) -> list[str]:
        """Prompt de chaque appel de l'Examinateur, dans l'ordre."""
        return [call.prompt for call in self.models.calls if call.agent == "examiner"]


type MakeQuiz = Callable[..., Awaitable[QuizRun]]


@pytest.fixture
async def quiz_store() -> FakeQuizStore:
    return FakeQuizStore()


@pytest.fixture
async def make_quiz_runner(
    tmp_path: Path,
    db_session_factory: async_sessionmaker[AsyncSession],
    user_id: str,
    other_user_id: str,
    quiz_store: FakeQuizStore,
) -> AsyncIterator[MakeQuiz]:
    """`make(models, mode=…)` lance `quiz` en mode `generate` (le quiz du faux port) ou `grade`
    (sa tentative). L'Examinateur rend `GOOD_QUIZ` et `GOOD_GRADES` par défaut, après les règles
    du test. `start=False` : pas de départ ; `sid=` reprend une session existante (nouveau
    « processus » : même base, même `checkpoints.db`, même port)."""
    await add_users(db_session_factory, user_id, other_user_id)
    quiz_store.add_material(user_id)
    if (user_id, ATTEMPT_ID) not in quiz_store.attempts:
        quiz_store.add_attempt(user_id)
    async with AsyncExitStack() as stack:

        async def make(
            models: CouncilModels | None = None,
            *,
            mode: str = "generate",
            sid: str | None = None,
            start: bool = True,
        ) -> QuizRun:
            models = models or CouncilModels()
            models.when("examiner", WRITE_REQUEST, *[GOOD_QUIZ] * 20)  # après celles du test
            models.when("examiner", GRADE_REQUEST, *[GOOD_GRADES] * 20)
            saver = await stack.enter_async_context(open_checkpointer(tmp_path / "checkpoints.db"))
            bus = EventBus(db_session_factory)
            runner = SessionRunner(
                session_factory=db_session_factory,
                bus=bus,
                models=models,
                checkpointer=saver,
                prices={"modele-test": ModelPrice(1.0, 2.0)},
                run_settings=_Settings(),
                ports=AgentPorts(quiz=quiz_store),
            )
            stack.push_async_callback(bus.aclose)
            stack.push_async_callback(runner.shutdown)
            run = QuizRun(runner, db_session_factory, quiz_store, models, user_id)
            if sid is not None:
                run.sid = sid
            elif start:
                run.sid = await runner.start(user_id, "quiz", BODIES[mode])
            return run

        yield make
