"""Matériel des tests du parcours `learning_council` : le runner de `make_web_runner` (vraie
mémoire, vraie recherche sur de faux moteurs, faux LLM) avec un faux port du Conseil en mémoire
(`FakeCouncilStore`). Aucun réseau ni LLM réel."""

import json
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import pytest

from app.agents.runtime.runner import SessionRunner
from app.db.models.agents import AgentSession
from app.providers.search.base import SearchResult
from app.providers.web.base import WebDocument
from tests.agents.graphs.web_support import SCORE_82, MakeWeb, Web
from tests.agents.runtime.runner_helpers import all_events, get_session, wait_status
from tests.support.council import GOAL_ID, FakeCouncilStore

QUERY = "ai product engineer"
PLAN = json.dumps({"queries": [{"text": QUERY, "lang": "fr"}]})
PAGE_COUNT = 9
URLS = [f"https://site{n}.exemple.org/article" for n in range(PAGE_COUNT)]
ADA_URL = URLS[0]
PEOPLE = json.dumps(
    {
        "people": [
            {"name": "Ada Lovelace", "role": "Ingénieure IA", "urls": [ADA_URL, URLS[1]]},
            {"name": "Inventée", "role": "Personne", "urls": ["https://invente.exemple/x"]},
        ]
    }
)


def framing_replies(count: int) -> list[str]:
    questions = [{"question": f"Question de cadrage numéro {n} ?"} for n in range(1, count + 1)]
    return [json.dumps({"questions": questions})]


def research_replies(people: str = PEOPLE) -> list[str]:
    """Après le cadrage : le plan, une note par page, puis les praticiens."""
    return [PLAN, *[SCORE_82] * PAGE_COUNT, people]


@dataclass
class Council:
    runner: SessionRunner
    web: Web
    store: FakeCouncilStore
    user_id: str
    sid: str = ""

    async def wait_status(self, status: str) -> AgentSession:
        return await wait_status(self.web.factory, self.user_id, self.sid, status)

    async def resume(self, value: Any) -> None:
        row = await get_session(self.web.factory, self.user_id, self.sid)
        pending = row.pending_interrupt or {}
        await self.runner.resume(self.user_id, self.sid, pending.get("interrupt_id"), value)

    async def events(self, type_: str) -> list[dict[str, Any]]:
        events = await all_events(self.web.factory, self.user_id, self.sid)
        return [e.payload.model_dump() for e in events if e.type == type_]

    async def source_found(self) -> list[dict[str, Any]]:
        return await self.events("source.found")

    def prompts(self) -> list[str]:
        """Texte de chaque appel au faux LLM, dans l'ordre."""
        assert self.web.fake is not None
        return ["\n".join(str(m.content) for m in call) for call in self.web.fake.received]

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
    """`make(replies)` démarre un Conseil sur l'objectif du faux port ; `sid=` reprend une
    session existante (nouveau « processus » : même base, même port, mêmes faux moteurs).
    `models` remplace le faux LLM."""
    store = FakeCouncilStore()
    store.add_goal(user_id)

    async def make(replies: list[str], *, models: Any = None, sid: str | None = None) -> Council:
        web = await make_web_runner(replies, models=models, council=store)
        script_council_web(web)
        council = Council(web.runner, web, store, user_id)
        council.sid = sid or await web.runner.start(
            user_id, "learning_council", {"goal_id": GOAL_ID}
        )
        return council

    yield make
