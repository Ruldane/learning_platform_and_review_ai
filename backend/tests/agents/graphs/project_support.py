"""Matériel des tests des parcours `project_brief` et `project_review` : runner sur le registre
réel, faux modèles par agent (`CouncilModels`, qui gardent chaque prompt), faux port des projets
(`FakeProjectStore`) et réponses scriptées du Praticien. Aucun réseau ni LLM réel."""

import json
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AsyncExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.nodes.practitioner import brief as brief_node
from app.agents.nodes.practitioner import drafts as drafts_node
from app.agents.nodes.practitioner import evaluate as evaluate_node
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
from tests.support.projects import PROJECT_ID, FakeProjectStore

BRIEF_ASK = brief_node.ASK
EVALUATE_ASK = evaluate_node.ASK
DRAFTS_ASK = drafts_node.ASK
_SENTENCE = "Chaque route valide ses entrées avant de répondre, ce qui m'a appris les modèles."
CLEAN_POST = " ".join(
    ["J'ai construit une API de suivi de lecture avec FastAPI et Pydantic, avec des tests."]
    + [_SENTENCE] * 5
)
SECRET_POST = (
    "J'ai lancé mon API : 10 000 utilisateurs et un déploiement sur Kubernetes. "
    + "Je suis fière de ce travail d'équipe et de ce que j'ai appris sur les routes. " * 6
)


def brief_json(**over: Any) -> str:
    data: dict[str, Any] = {
        "title": "Une API de suivi de lecture",
        "context": "Une petite équipe veut suivre ses lectures.",
        "objective": "Construire une API de suivi de lecture.",
        "constraints": ["Utiliser FastAPI.", "Aucun service payant."],
        "criteria": ["Trois routes documentées.", "Entrées validées.", "Des tests qui passent."],
        "hours": 4,
        "deliverable": "either",
    }
    return json.dumps(data | over)


def evaluation_json(met: list[bool], feedback: str = "Un rendu clair.") -> str:
    results = [{"index": i, "met": ok, "comment": f"Critère {i}."} for i, ok in enumerate(met, 1)]
    return json.dumps({"results": results, "feedback": feedback})


def all_met(count: int) -> str:
    return evaluation_json([True] * count)


def drafts_json(**over: Any) -> str:
    data: dict[str, Any] = {
        "cv_line": "Conçu une API de suivi de lecture avec FastAPI et Pydantic.",
        "profile_entry": {
            "name": "API de suivi de lecture",
            "description": "Une API construite avec FastAPI et Pydantic, avec des tests.",
            "achievements": ["Validation des entrées avec Pydantic."],
        },
        "linkedin_post": CLEAN_POST,
        "readme_plan": ["Présentation", "Installation", "Utilisation", "Tests", "Limites"],
    }
    return json.dumps(data | over)


def project_models(
    *,
    brief: list[str] | None = None,
    evaluation: list[str] | None = None,
    drafts: list[str] | None = None,
) -> CouncilModels:
    """Faux modèles : le Praticien rend `brief`, `evaluation` ou `drafts` selon la demande."""
    models = CouncilModels()
    models.when("practitioner", BRIEF_ASK, *(brief or []))
    models.when("practitioner", EVALUATE_ASK, *(evaluation or []))
    models.when("practitioner", DRAFTS_ASK, *(drafts or []))
    return models


def prompts(models: CouncilModels, marker: str) -> list[str]:
    return [c.prompt for c in models.calls if marker in c.prompt]


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
class ProjectRun:
    runner: SessionRunner
    factory: async_sessionmaker[AsyncSession]
    store: FakeProjectStore
    models: CouncilModels
    user_id: str
    sid: str = ""

    async def wait_status(self, status: str) -> AgentSession:
        return await wait_status(self.factory, self.user_id, self.sid, status)

    async def events(self, type_: str) -> list[dict[str, Any]]:
        events = await all_events(self.factory, self.user_id, self.sid)
        return [e.payload.model_dump() for e in events if e.type == type_]

    def calls(self, marker: str) -> int:
        return len(prompts(self.models, marker))


type MakeProject = Callable[..., Awaitable[ProjectRun]]


@pytest.fixture
def project_store() -> FakeProjectStore:
    return FakeProjectStore()


@pytest.fixture
async def project_runner(
    tmp_path: Path,
    db_session_factory: async_sessionmaker[AsyncSession],
    user_id: str,
    other_user_id: str,
    project_store: FakeProjectStore,
) -> AsyncIterator[MakeProject]:
    """`make(models, graph=...)` lance `project_review` (ou `project_brief`) ; `sid=` reprend une
    session existante (nouveau « processus » : même base, même `checkpoints.db`, même port)."""
    await add_users(db_session_factory, user_id, other_user_id)
    async with AsyncExitStack() as stack:

        async def make(
            models: CouncilModels, *, graph: str = "project_review", sid: str | None = None
        ) -> ProjectRun:
            saver = await stack.enter_async_context(open_checkpointer(tmp_path / "checkpoints.db"))
            bus = EventBus(db_session_factory)
            runner = SessionRunner(
                session_factory=db_session_factory,
                bus=bus,
                models=models,
                checkpointer=saver,
                prices={"modele-test": ModelPrice(1.0, 2.0)},
                run_settings=_Settings(),
                ports=AgentPorts(projects=project_store),
            )
            stack.push_async_callback(bus.aclose)
            stack.push_async_callback(runner.shutdown)
            run = ProjectRun(runner, db_session_factory, project_store, models, user_id)
            run.sid = sid or await runner.start(user_id, graph, {"project_id": PROJECT_ID})
            return run

        yield make
