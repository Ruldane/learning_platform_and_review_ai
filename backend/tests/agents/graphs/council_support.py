"""Matériel des tests du parcours `learning_council` : le runner de `make_web_runner` (vraie
mémoire, vraie recherche sur de faux moteurs) avec les faux modèles du Conseil
(`CouncilModels` : script commun puis réponses par agent) et un faux port du Conseil en mémoire
(`FakeCouncilStore`). Aucun réseau ni LLM réel."""

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import pytest

from app.agents.runtime.events import UserCommand
from app.agents.runtime.runner import SessionRunner
from app.db.models.agents import AgentSession
from app.providers.search.base import SearchResult
from app.providers.web.base import WebDocument
from tests.agents.graphs.council_models import (
    ADA_URL,
    PAGE_COUNT,
    PEOPLE,
    PLAN,
    QUERY,
    URLS,
    CouncilModels,
)
from tests.agents.graphs.web_support import SCORE_82, MakeWeb, Web
from tests.agents.runtime.runner_helpers import TIMEOUT, all_events, get_session, wait_status
from tests.support.council import GOAL_ID, FakeCouncilStore

__all__ = ["ADA_URL", "PAGE_COUNT", "Council", "MakeCouncil", "Said"]


def framing_replies(count: int) -> list[str]:
    questions = [{"question": f"Question de cadrage numéro {n} ?"} for n in range(1, count + 1)]
    return [json.dumps({"questions": questions})]


def research_replies(people: str = PEOPLE) -> list[str]:
    """Après le cadrage : le plan, une note par page, puis les praticiens."""
    return [PLAN, *[SCORE_82] * PAGE_COUNT, people]


@dataclass(frozen=True)
class Said:
    """Un `agent.message`, avec l'étape annoncée par le dernier `agent.started` de son agent."""

    agent: str
    step: str
    payload: dict[str, Any]


@dataclass
class Council:
    runner: SessionRunner
    web: Web
    store: FakeCouncilStore
    models: CouncilModels
    user_id: str
    sid: str = ""
    pending: dict[str, Any] | None = None

    async def wait_status(self, status: str) -> AgentSession:
        return await wait_status(self.web.factory, self.user_id, self.sid, status)

    async def wait_question(
        self, kind: str, *, after: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Attend la question `kind` en attente (et la garde dans `pending`) ; `after` : une
        question nouvelle, pas celle-ci."""
        old = (after or {}).get("interrupt_id")
        async with asyncio.timeout(TIMEOUT * 4):
            while True:
                row = await get_session(self.web.factory, self.user_id, self.sid)
                pending = row.pending_interrupt or {}
                fresh = pending.get("interrupt_id") != old
                if row.status == "waiting_user" and pending.get("kind") == kind and fresh:
                    self.pending = pending
                    return pending
                assert row.status not in ("failed", "completed"), row.error
                await asyncio.sleep(0.01)

    async def wait_choice(self, *, after: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self.wait_question("choose_path", after=after)

    async def resume(self, value: Any) -> None:
        row = await get_session(self.web.factory, self.user_id, self.sid)
        pending = row.pending_interrupt or {}
        await self.runner.resume(self.user_id, self.sid, pending.get("interrupt_id"), value)

    async def to_choice(self) -> dict[str, Any]:
        """Cadrage passé (« go »), puis attente du choix du parcours."""
        await self.wait_question("framing")
        await self.resume("go")
        return await self.wait_choice()

    async def post_message(self, text: str, command: UserCommand | None = None) -> None:
        await self.runner.post_message(self.user_id, self.sid, text, command)

    async def events(self, type_: str) -> list[dict[str, Any]]:
        events = await all_events(self.web.factory, self.user_id, self.sid)
        return [e.payload.model_dump() for e in events if e.type == type_]

    async def source_found(self) -> list[dict[str, Any]]:
        return await self.events("source.found")

    async def agent_messages(self, *, step_prefix: str = "") -> list[Said]:
        steps: dict[str, str] = {}
        said: list[Said] = []
        for event in await all_events(self.web.factory, self.user_id, self.sid):
            payload = event.payload.model_dump()
            agent = event.agent or ""
            if event.type == "agent.started":
                steps[agent] = payload["step"]
            elif event.type == "agent.message" and steps.get(agent, "").startswith(step_prefix):
                said.append(Said(agent, steps.get(agent, ""), payload))
        return said

    def prompts(self) -> list[str]:
        """Texte de chaque appel au faux LLM, dans l'ordre."""
        return [call.prompt for call in self.models.calls]

    def prompt_of(self, said: Said) -> str:
        """Prompt de l'appel qui a produit ce message (`message_id` = `fake-<rang>`)."""
        return self.models.calls[int(said.payload["message_id"].removeprefix("fake-"))].prompt

    def search_queries_prompt(self) -> str:
        """Prompt du nœud `plan` de l'Éclaireur."""
        return next(p for p in self.prompts() if "Prépare les requêtes de recherche." in p)

    def people_prompt(self) -> str:
        return next(p for p in self.prompts() if "Repère les praticiens." in p)


type MakeCouncil = Callable[..., Awaitable[Council]]


def script_council_web(web: Web) -> None:
    web.search.results[QUERY] = [
        SearchResult(title=f"Titre {n}", url=u, snippet="extrait", engine="fake", published=None)
        for n, u in enumerate(URLS)
    ]
    for n, url in enumerate(URLS):
        author = "Ada Lovelace" if n == 0 else None
        web.reader.pages[url] = WebDocument(
            url, f"Article {n}", "Texte de la page.", author, "2026-01-02", "fr", None
        )


@pytest.fixture
async def make_council_runner(make_web_runner: MakeWeb, user_id: str) -> AsyncIterator[MakeCouncil]:
    """`make(replies)` démarre un Conseil sur l'objectif du faux port : `replies` d'abord (tous
    agents confondus), puis les réponses par défaut de chaque agent. `sid=` reprend une session
    existante (nouveau « processus » : même base, même port, mêmes faux moteurs) ; `models`
    remplace les faux modèles ; `rounds` (`debate_rounds`, 1 par défaut) et `token_cap`."""
    store = FakeCouncilStore()
    store.add_goal(user_id)

    async def make(
        replies: list[str] | None = None,
        *,
        models: CouncilModels | None = None,
        sid: str | None = None,
        rounds: int = 1,
        token_cap: int = 300_000,
    ) -> Council:
        models = models or CouncilModels(list(replies or []))
        web = await make_web_runner(
            [], models=models, council=store, rounds=rounds, token_cap=token_cap
        )
        script_council_web(web)
        council = Council(web.runner, web, store, models, user_id)
        council.sid = sid or await web.runner.start(
            user_id, "learning_council", {"goal_id": GOAL_ID}
        )
        return council

    yield make
