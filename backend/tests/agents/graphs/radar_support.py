"""Matériel des tests du parcours `market_radar` : runner sur le registre réel, faux modèles par
agent (`CouncilModels`, qui gardent chaque prompt), faux port du radar (`FakeRadarStore`) et
fausse recherche web. Aucun réseau ni LLM réel."""

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.nodes.analyst_radar import RADAR_REQUEST
from app.agents.runtime.bus import EventBus
from app.agents.runtime.checkpointer import open_checkpointer
from app.agents.runtime.costs import ModelPrice
from app.agents.runtime.ports import AgentPorts
from app.agents.runtime.run_settings import RunSettings
from app.agents.runtime.runner import SessionRunner
from app.agents.tools.web_port import WebHit, WebLimits, WebSearchResult
from app.core.errors import AppError
from app.db.models.agents import AgentSession
from tests.agents.graphs.council_models import CouncilModels
from tests.agents.graphs.web_support import add_users
from tests.agents.runtime.runner_helpers import all_events, get_session, wait_status
from tests.support.radar import RUN_ID, FakeRadarStore, Source

TEXT = (
    "Nous recrutons un ingénieur IA pour notre équipe produit. Missions : concevoir des "
    "assistants, évaluer des systèmes RAG, industrialiser avec Docker et LangGraph. "
    "Rémunération : 45 000 à 55 000 euros par an. Télétravail partiel possible."
)


def link(number: int, host: str = "jobs.example.org") -> str:
    return f"https://{host}/offre/{number}"


def postings(count: int, *, start: int = 0, text: str = TEXT) -> list[Source]:
    return [Source(link(n), "ok", f"{text} Référence {n}.") for n in range(start, start + count)]


def blocked(count: int, *, start: int = 1000) -> list[Source]:
    return [
        Source(link(n, "bloque.example.org"), "unreadable") for n in range(start, start + count)
    ]


def item(ref: str, **over: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "ref": ref,
        "is_job_posting": True,
        "title": "Ingénieur IA",
        "company": "Société Fictive",
        "level": "confirme",
        "remote": "partiel",
        "salary": "45 000 à 55 000 euros",
        "skills": [{"name": "Python", "required": True}, {"name": "RAG", "required": False}],
        "tools": ["Docker", "LangGraph"],
    }
    return data | over


def batch(count: int, **over: Any) -> str:
    """La réponse de l'Analyste pour un lot de `count` offres (`p1` à `p<count>`)."""
    return json.dumps({"items": [item(f"p{n}", **over) for n in range(1, count + 1)]})


def analyst(*replies: str, default: int = 20) -> CouncilModels:
    """Faux modèles : l'Analyste rend `replies`, puis des lots de cinq offres valables."""
    models = CouncilModels()
    models.when("analyst", RADAR_REQUEST, *replies, *[batch(5)] * default)
    return models


def analyst_prompts(models: CouncilModels) -> list[str]:
    return [c.prompt for c in models.calls if c.agent == "analyst" and RADAR_REQUEST in c.prompt]


@dataclass
class FakeRadarWeb:
    """Recherche web factice : la première requête qui répond rend `urls`, les autres rien (sauf
    `per_query`)."""

    urls: list[str] = field(default_factory=list)
    per_query: dict[str, list[str]] = field(default_factory=dict)
    fail_with: AppError | None = None  # toutes les requêtes échouent
    fail_queries: set[str] = field(default_factory=set)  # ces requêtes échouent
    served: bool = False
    searches: list[tuple[str, str | None, str | None]] = field(default_factory=list)

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
        if self.fail_with is not None:
            raise self.fail_with
        if query in self.fail_queries:
            raise AppError("search_unavailable", "Brut.", 503)
        urls = self.per_query.get(query, [] if self.served else self.urls)
        self.served = True
        hits = [WebHit("Offre", url, "Extrait", "fake", None, False) for url in urls]
        return WebSearchResult(query, "searxng", hits)

    async def limits(self, user_id: str) -> WebLimits:
        return WebLimits(("fr",), (), 12, 30)


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
class RadarRun:
    runner: SessionRunner
    factory: async_sessionmaker[AsyncSession]
    store: FakeRadarStore
    web: FakeRadarWeb
    models: CouncilModels
    user_id: str
    sid: str = ""

    async def wait_status(self, status: str, timeout: float | None = None) -> AgentSession:
        """`timeout` : garde contre un blocage (par défaut celui des autres tests du moteur)."""
        if timeout is None:
            return await wait_status(self.factory, self.user_id, self.sid, status)
        async with asyncio.timeout(timeout):
            while (row := await get_session(self.factory, self.user_id, self.sid)).status != status:
                await asyncio.sleep(0.01)
        return row

    async def events(self, type_: str) -> list[dict[str, Any]]:
        events = await all_events(self.factory, self.user_id, self.sid)
        return [e.payload.model_dump() for e in events if e.type == type_]

    async def types(self) -> list[str]:
        return [e.type for e in await all_events(self.factory, self.user_id, self.sid)]

    async def said(self) -> list[str]:
        return [e["text"] for e in await self.events("agent.message")]


type MakeRadar = Callable[..., Awaitable[RadarRun]]


@pytest.fixture
def radar_store() -> FakeRadarStore:
    return FakeRadarStore()


@pytest.fixture
def radar_web() -> FakeRadarWeb:
    return FakeRadarWeb()


@pytest.fixture
async def radar_runner(
    tmp_path: Path,
    db_session_factory: async_sessionmaker[AsyncSession],
    user_id: str,
    other_user_id: str,
    radar_store: FakeRadarStore,
    radar_web: FakeRadarWeb,
) -> AsyncIterator[MakeRadar]:
    """`make(models, sources=…)` lance `market_radar` : `sources` sont les pages du faux web (leurs
    liens sont ceux que la recherche rend) ; `sid=` reprend une session existante (nouveau
    « processus » : même base, même `checkpoints.db`, même port)."""
    await add_users(db_session_factory, user_id, other_user_id)
    async with AsyncExitStack() as stack:

        async def make(
            models: CouncilModels | None = None,
            *,
            sources: list[Source] | None = None,
            sid: str | None = None,
            store: Any = None,
        ) -> RadarRun:
            models = models or analyst()
            if sources is not None:
                radar_store.serve(*sources)
                radar_web.urls = [source.url for source in sources]
            saver = await stack.enter_async_context(open_checkpointer(tmp_path / "checkpoints.db"))
            bus = EventBus(db_session_factory)
            runner = SessionRunner(
                session_factory=db_session_factory,
                bus=bus,
                models=models,
                checkpointer=saver,
                prices={"modele-test": ModelPrice(1.0, 2.0)},
                run_settings=_Settings(),
                ports=AgentPorts(web=radar_web, radar=store if store is not None else radar_store),
            )
            stack.push_async_callback(bus.aclose)
            stack.push_async_callback(runner.shutdown)
            run = RadarRun(
                runner, db_session_factory, store or radar_store, radar_web, models, user_id
            )
            run.sid = sid or await runner.start(user_id, "market_radar", {"run_id": RUN_ID})
            return run

        yield make
