"""Matériel des tests du parcours `application_kit` : runner sur le registre réel, faux modèles par
agent (`CouncilModels`, qui gardent chaque prompt), faux port du kit (`FakeKitStore`) et fausse
recherche web. Aucun réseau ni LLM réel."""

import json
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AsyncExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.nodes.scout.dossier import DOSSIER_REQUEST
from app.agents.nodes.tracker.pieces import SPECS
from app.agents.runtime.bus import EventBus
from app.agents.runtime.checkpointer import open_checkpointer
from app.agents.runtime.costs import ModelPrice
from app.agents.runtime.ports import AgentPorts
from app.agents.runtime.run_settings import RunSettings
from app.agents.runtime.runner import SessionRunner
from app.db.models.agents import AgentSession
from tests.agents.graphs.council_models import CouncilModels
from tests.agents.graphs.review_support import FakeWeb
from tests.agents.graphs.web_support import add_users
from tests.agents.runtime.runner_helpers import all_events, wait_status
from tests.support.kit import APPLICATION_ID, COMPANY, TITLE, FakeKitStore

STYLE = "Ton chaleureux, phrases courtes, aucune formule creuse."
_BASE = "Je construis des solutions fiables avec soin et je partage ce que j'apprends chaque jour."
OPENING = f"Bonjour, je candidate à votre poste de {TITLE} chez {COMPANY}."


def filler(count: int) -> str:
    """`count` mots ordinaires, qu'aucun contrôle de faits ne signale."""
    words = (_BASE.split() * (count // 15 + 1))[:count]
    return " ".join(words)


def letter_text(words: int = 300) -> str:
    return f"{OPENING} {filler(words - len(OPENING.split()))}"


def letter(words: int = 300) -> str:
    return json.dumps({"text": letter_text(words)}, ensure_ascii=False)


def linkedin(message_words: int = 100) -> str:
    invitation = f"Bonjour, votre poste de {TITLE} m'intéresse, je serais ravie d'échanger."
    return json.dumps({"invitation": invitation, "message": filler(message_words)})


def followups(words: int = 80) -> str:
    return json.dumps({"day_7": filler(words), "day_14": filler(words)})


def pitch(words: int = 150) -> str:
    return json.dumps({"text": filler(words)})


def answer(question: str, text: str, *facts: str) -> dict[str, Any]:
    return {"question": question, "answer": text, "fact_ids": list(facts)}


PERMIT = answer("Avez-vous le permis B ?", "Oui, je conduis régulièrement.", "x1")
SALARY = answer("Quelles sont vos prétentions salariales ?", "45 k€ brut annuel.", "x1")
NO_FACT = answer("Quelle est votre disponibilité ?", "Immédiate.")


def form(*items: dict[str, Any]) -> str:
    return json.dumps({"items": list(items)}, ensure_ascii=False)


QUESTIONS = [f"Question {chr(97 + rank)} sur l'équipe ?" for rank in range(5)]


def dossier_data(**over: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "activity": "Éditeur d'assistants pour le support client [1].",
        "product": "Une plateforme d'agents conversationnels [1, 2].",
        "stack": ["Python [1]", "Docker [2]"],
        "news": [{"text": "Levée de fonds annoncée [2]", "date": "2026-10-01"}],
        "culture": "Équipe réduite, décisions rapides [2].",
        "interview_process": "Trois entretiens, dont un technique [1].",
        "questions": QUESTIONS,
        "watch_points": ["Rythme soutenu [1]"],
        "size": "sme",
    }
    return data | over


def dossier(**over: Any) -> str:
    return json.dumps(dossier_data(**over), ensure_ascii=False)


DEFAULTS: dict[str, str] = {
    "letter": letter(),
    "linkedin": linkedin(),
    "followups": followups(),
    "pitch": pitch(),
    "form_answers": form(PERMIT),
}


def writers(**replies: list[str]) -> CouncilModels:
    """Faux modèles : les réponses du test d'abord (par pièce), puis les réponses valables."""
    models = CouncilModels()
    for kind, spec in SPECS.items():
        models.when("tracker", spec.request, *replies.get(kind, []), *[DEFAULTS[kind]] * 10)
    models.when("scout", DOSSIER_REQUEST, *replies.get("dossier", []), *[dossier()] * 5)
    return models


def prompts(models: CouncilModels, kind: str) -> list[str]:
    """Les prompts de la pièce `kind` (le marqueur : son message de demande)."""
    marker = DOSSIER_REQUEST if kind == "dossier" else SPECS[kind].request
    return [c.prompt for c in models.calls if marker in c.prompt]


class _Settings:
    async def get_run_settings(self, user_id: str) -> RunSettings:
        return RunSettings(
            session_token_cap=1_000_000,
            debate_rounds=1,
            lesson_language="fr",
            search_languages=("fr",),
            style_guide=STYLE,
        )


@dataclass
class KitRun:
    runner: SessionRunner
    factory: async_sessionmaker[AsyncSession]
    store: FakeKitStore
    web: FakeWeb
    models: CouncilModels
    user_id: str
    sid: str = ""

    async def wait_status(self, status: str) -> AgentSession:
        return await wait_status(self.factory, self.user_id, self.sid, status)

    async def events(self, type_: str) -> list[dict[str, Any]]:
        events = await all_events(self.factory, self.user_id, self.sid)
        return [e.payload.model_dump() for e in events if e.type == type_]

    async def titles(self) -> list[str]:
        return [e["title"] for e in await self.events("artifact.ready")]


type MakeKit = Callable[..., Awaitable[KitRun]]


@pytest.fixture
def kit_store() -> FakeKitStore:
    return FakeKitStore()


@pytest.fixture
def kit_web() -> FakeWeb:
    return FakeWeb()


@pytest.fixture
async def kit_runner(
    tmp_path: Path,
    db_session_factory: async_sessionmaker[AsyncSession],
    user_id: str,
    other_user_id: str,
    kit_store: FakeKitStore,
    kit_web: FakeWeb,
) -> AsyncIterator[MakeKit]:
    """`make(models)` lance `application_kit` ; `sid=` reprend une session existante (nouveau
    « processus » : même base, même `checkpoints.db`, même port)."""
    await add_users(db_session_factory, user_id, other_user_id)
    async with AsyncExitStack() as stack:

        async def make(models: CouncilModels | None = None, *, sid: str | None = None) -> KitRun:
            models = models or writers()
            saver = await stack.enter_async_context(open_checkpointer(tmp_path / "checkpoints.db"))
            bus = EventBus(db_session_factory)
            runner = SessionRunner(
                session_factory=db_session_factory,
                bus=bus,
                models=models,
                checkpointer=saver,
                prices={"modele-test": ModelPrice(1.0, 2.0)},
                run_settings=_Settings(),
                ports=AgentPorts(kit=kit_store, web=kit_web),  # type: ignore[arg-type]
            )
            stack.push_async_callback(bus.aclose)
            stack.push_async_callback(runner.shutdown)
            run = KitRun(runner, db_session_factory, kit_store, kit_web, models, user_id)
            run.sid = sid or await runner.start(
                user_id, "application_kit", {"application_id": APPLICATION_ID}
            )
            return run

        yield make
