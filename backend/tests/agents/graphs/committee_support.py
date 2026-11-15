"""Matériel des tests du parcours `hiring_committee` : runner sur le registre réel, faux modèles par
persona (`CouncilModels`, qui garde chaque prompt) et faux port du comité (`FakeCommitteeStore`).
Aucun réseau ni LLM réel."""

import json
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from contextlib import AsyncExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.nodes.committee.common import (
    DEBATE_REQUEST,
    IMPRESSION_REQUEST,
    SYNTHESIS_REQUEST,
    VOTE_REQUEST,
)
from app.agents.runtime.bus import EventBus
from app.agents.runtime.checkpointer import open_checkpointer
from app.agents.runtime.costs import ModelPrice
from app.agents.runtime.ports import AgentPorts
from app.agents.runtime.run_settings import RunSettings
from app.agents.runtime.runner import SessionRunner
from app.agents.tools.committee_schema import PERSONAS
from app.db.models.agents import AgentSession
from tests.agents.graphs.council_models import CouncilModels
from tests.agents.graphs.web_support import add_users
from tests.agents.runtime.runner_helpers import all_events, get_session, wait_status
from tests.support.committee import RUN_ID, FakeCommitteeStore

IMPRESSIONS = {
    "ats_reader": "Le CV remonte sur Python et Docker, mais pas sur LangGraph.",
    "recruiter": "Un parcours lisible, des résultats chiffrés, une page.",
    "manager": "Je vois quelqu'un de solide, à vérifier sur les agents.",
    "colleague": "Un profil crédible, ouvert à l'équipe.",
}
SPEECHES = {
    "ats_reader": "Je réponds au Manager et au Recruteur : le filtre laisse passer Python.",
    "recruiter": "Je rejoins le Lecteur ATS et le Manager : le CV est clair et lisible.",
    "manager": "Je réponds au Recruteur et au Futur collègue : il manque des agents en production.",
    "colleague": "Je suis d'accord avec le Manager et le Lecteur ATS sur les agents.",
}
OBJECTIONS = {
    "ats_reader": "Aucun mot clé LangGraph dans le CV",
    "recruiter": "Le résultat chiffré est enfoui dans une phrase",
    "manager": "Pas d'agent mis en production",
    "colleague": "Peu de travail d'équipe visible",
}
CHANGES = [
    {"text": "Mettre le résultat de 30 % en tête de la ligne", "persona": "recruiter",
     "fact_ids": ["x1a1"]},
    {"text": "Placer le projet d'agent en premier", "persona": "manager", "fact_ids": ["x1"]},
    {"text": "Écrire Python et Docker comme l'offre", "persona": "ats_reader",
     "fact_ids": ["c1", "c2"]},
]  # fmt: skip


def vote_json(vote: str = "oui", persona: str = "recruiter", **over: Any) -> str:
    data: dict[str, Any] = {
        "vote": vote,
        "objection": OBJECTIONS[persona],
        "reason": f"Raison de {persona}.",
    }
    return json.dumps(data | over, ensure_ascii=False)


def synthesis_json(
    changes: Sequence[dict[str, Any]] | None = None,
    objections: Sequence[dict[str, Any]] | None = None,
) -> str:
    ranked = objections or [
        {"text": OBJECTIONS["ats_reader"], "personas": ["ats_reader"]},
        {"text": OBJECTIONS["manager"], "personas": ["manager", "colleague"]},
    ]
    return json.dumps(
        {"objections": list(ranked), "changes": list(changes or CHANGES)}, ensure_ascii=False
    )


def committee(
    *,
    votes: dict[str, str] | None = None,
    speeches: dict[str, str] | None = None,
    synthesis: str | None = None,
) -> CouncilModels:
    """Faux modèles : une impression et une parole par persona, des votes « oui » (sauf ceux de
    `votes`, persona → vote) et une synthèse valable. Les réponses se répètent à chaque appel."""
    models = CouncilModels()
    for persona in PERSONAS:
        said = (speeches or {}).get(persona, SPEECHES[persona])
        models.when(persona, IMPRESSION_REQUEST, *[IMPRESSIONS[persona]] * 3)
        models.when(persona, DEBATE_REQUEST, *[said] * 6)
        vote = (votes or {}).get(persona, "oui")
        models.when(persona, VOTE_REQUEST, *[vote_json(vote, persona)] * 3)
    models.when("moderator", SYNTHESIS_REQUEST, *[synthesis or synthesis_json()] * 3)
    return models


def prompts(models: CouncilModels, agent: str, request: str) -> list[str]:
    return [c.prompt for c in models.calls if c.agent == agent and request in c.prompt]


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
class CommitteeRun:
    runner: SessionRunner
    factory: async_sessionmaker[AsyncSession]
    store: FakeCommitteeStore
    models: CouncilModels
    user_id: str
    sid: str = ""

    async def wait_status(self, status: str) -> AgentSession:
        return await wait_status(self.factory, self.user_id, self.sid, status)

    async def events(self, type_: str) -> list[dict[str, Any]]:
        events = await all_events(self.factory, self.user_id, self.sid)
        return [e.payload.model_dump() for e in events if e.type == type_]

    async def messages(self, agent: str) -> list[str]:
        events = await all_events(self.factory, self.user_id, self.sid)
        return [
            e.payload.model_dump()["text"]
            for e in events
            if e.type == "agent.message" and e.agent == agent
        ]

    async def failed_code(self) -> str | None:
        row = await get_session(self.factory, self.user_id, self.sid)
        return (row.error or {}).get("code")


type MakeCommittee = Callable[..., Awaitable[CommitteeRun]]


@pytest.fixture
def committee_store() -> FakeCommitteeStore:
    return FakeCommitteeStore()


@pytest.fixture
async def committee_runner(
    tmp_path: Path,
    db_session_factory: async_sessionmaker[AsyncSession],
    user_id: str,
    other_user_id: str,
    committee_store: FakeCommitteeStore,
) -> AsyncIterator[MakeCommittee]:
    """`make(models)` lance `hiring_committee` ; `sid=` reprend une session existante (nouveau
    « processus » : même base, même `checkpoints.db`, même port)."""
    await add_users(db_session_factory, user_id, other_user_id)
    async with AsyncExitStack() as stack:

        async def make(
            models: CouncilModels | None = None, *, sid: str | None = None
        ) -> CommitteeRun:
            models = models or committee()
            saver = await stack.enter_async_context(open_checkpointer(tmp_path / "checkpoints.db"))
            bus = EventBus(db_session_factory)
            runner = SessionRunner(
                session_factory=db_session_factory,
                bus=bus,
                models=models,
                checkpointer=saver,
                prices={"modele-test": ModelPrice(1.0, 2.0)},
                run_settings=_Settings(),
                ports=AgentPorts(committee=committee_store),
            )
            stack.push_async_callback(bus.aclose)
            stack.push_async_callback(runner.shutdown)
            run = CommitteeRun(runner, db_session_factory, committee_store, models, user_id)
            run.sid = sid or await runner.start(user_id, "hiring_committee", {"run_id": RUN_ID})
            return run

        yield make
