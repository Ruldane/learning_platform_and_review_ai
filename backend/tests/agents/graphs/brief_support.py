"""Matériel des tests du parcours `daily_brief` : runner sur le registre réel, faux modèles par
agent (`CouncilModels`, qui gardent chaque prompt), faux port du brief (`FakeBriefStore`) et faux
web (recherche et lecture de pages). Aucun réseau ni LLM réel."""

import json
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.bus import EventBus
from app.agents.runtime.checkpointer import open_checkpointer
from app.agents.runtime.costs import ModelPrice
from app.agents.runtime.ports import AgentPorts
from app.agents.runtime.run_settings import RunSettings
from app.agents.runtime.runner import SessionRunner
from app.agents.tools.web_port import PageRead, WebHit, WebSearchResult
from app.db.models.agents import AgentSession
from tests.agents.graphs.council_models import CouncilModels
from tests.agents.graphs.web_support import add_users
from tests.agents.runtime.runner_helpers import all_events, wait_status
from tests.support.brief import BRIEF_ID, FakeBriefStore

PICK_MARKER = "Choisis la ressource du jour."
ADVICE_MARKER = "Écris le conseil du jour."
GOOD = ("Commence par ton bloc de 45 minutes.", "Puis passe tes 12 fiches en revue.")


def hit(number: int, **over: Any) -> WebHit:
    data: dict[str, Any] = {
        "title": f"Guide LangGraph partie {number}",
        "url": f"https://docs.exemple.org/guide/{number}",
        "snippet": f"Extrait du guide numéro {number}.",
        "engine": "fake",
        "published": f"2026-11-{number:02d}",
        "preferred": False,
    }
    return WebHit(**(data | over))


def hits(count: int = 5) -> list[WebHit]:
    return [hit(n) for n in range(1, count + 1)]


def pick(index: int | None, why: str = "Un guide clair et récent.") -> str:
    return json.dumps({"index": index, "why": why})


def advice(*sentences: str) -> str:
    return json.dumps({"sentences": list(sentences)})


def good_advice() -> str:
    return advice(*GOOD)


def brief_models(
    scout: list[str] | None = None, moderator: list[str] | None = None
) -> CouncilModels:
    """Faux modèles : l'Éclaireur rend `scout`, le Modérateur `moderator` (un conseil valable
    par défaut)."""
    models = CouncilModels()
    models.when("scout", PICK_MARKER, *(scout or []))
    models.when(
        "moderator", ADVICE_MARKER, *(moderator if moderator is not None else [good_advice()])
    )
    return models


def prompts(models: CouncilModels, agent: str) -> list[str]:
    return [c.prompt for c in models.calls if c.agent == agent]


@dataclass
class FakeBriefWeb:
    """Recherche web et lecture de pages factices : `results` pour toute requête ; une page se lit
    sauf si son lien est dans `unreadable` (ou `empty` : « lue » mais sans texte)."""

    results: list[WebHit] = field(default_factory=lambda: hits())
    unreadable: set[str] = field(default_factory=set)
    empty: set[str] = field(default_factory=set)
    search_error: Exception | None = None
    searches: list[tuple[str, str | None, str | None]] = field(default_factory=list)
    reads: list[str] = field(default_factory=list)

    async def search(
        self,
        user_id: str,
        session_id: str,
        query: str,
        *,
        lang: str | None = None,
        time_range: str | None = None,
        **_: Any,
    ) -> WebSearchResult:
        self.searches.append((query, lang, time_range))
        if self.search_error is not None:
            raise self.search_error
        return WebSearchResult(query, "searxng", list(self.results))

    async def read(self, user_id: str, session_id: str, url: str) -> PageRead:
        self.reads.append(url)
        bad = url in self.unreadable
        text = "" if bad or url in self.empty else "Le texte de la page."
        return PageRead(
            None,
            url,
            "unreadable" if bad else "ok",
            "Titre de la page",
            text,
            None,
            None,
            "fr",
            "blocked" if bad else None,
        )


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
class BriefRun:
    runner: SessionRunner
    factory: async_sessionmaker[AsyncSession]
    store: FakeBriefStore
    web: FakeBriefWeb
    models: CouncilModels
    user_id: str
    sid: str = ""

    async def wait_status(self, status: str) -> AgentSession:
        return await wait_status(self.factory, self.user_id, self.sid, status)

    async def events(self, type_: str) -> list[dict[str, Any]]:
        events = await all_events(self.factory, self.user_id, self.sid)
        return [e.payload.model_dump() for e in events if e.type == type_]

    async def types(self) -> list[str]:
        return [e.type for e in await all_events(self.factory, self.user_id, self.sid)]

    def calls(self, agent: str) -> int:
        return len(prompts(self.models, agent))


type MakeBrief = Callable[..., Awaitable[BriefRun]]


@pytest.fixture
def brief_store() -> FakeBriefStore:
    return FakeBriefStore()


@pytest.fixture
def brief_web() -> FakeBriefWeb:
    return FakeBriefWeb()


@pytest.fixture
async def brief_runner(
    tmp_path: Path,
    db_session_factory: async_sessionmaker[AsyncSession],
    user_id: str,
    other_user_id: str,
    brief_store: FakeBriefStore,
    brief_web: FakeBriefWeb,
) -> AsyncIterator[MakeBrief]:
    """`make(models)` lance `daily_brief` ; `sid=` reprend une session existante (nouveau
    « processus » : même base, même `checkpoints.db`, même port)."""
    await add_users(db_session_factory, user_id, other_user_id)
    async with AsyncExitStack() as stack:

        async def make(models: CouncilModels | None = None, *, sid: str | None = None) -> BriefRun:
            models = models or brief_models([pick(2)])
            saver = await stack.enter_async_context(open_checkpointer(tmp_path / "checkpoints.db"))
            bus = EventBus(db_session_factory)
            runner = SessionRunner(
                session_factory=db_session_factory,
                bus=bus,
                models=models,
                checkpointer=saver,
                prices={"modele-test": ModelPrice(1.0, 2.0)},
                run_settings=_Settings(),
                ports=AgentPorts(web=brief_web, brief=brief_store),
            )
            stack.push_async_callback(bus.aclose)
            stack.push_async_callback(runner.shutdown)
            run = BriefRun(runner, db_session_factory, brief_store, brief_web, models, user_id)
            run.sid = sid or await runner.start(user_id, "daily_brief", {"brief_id": BRIEF_ID})
            return run

        yield make
