"""Matériel des tests du parcours `cv_review` : runner sur le registre réel, faux modèles par agent
(`CouncilModels`, qui gardent chaque prompt), faux port de la revue (`FakeCvReviewStore`), faux
port de l'analyse (`FakeGapStore`) et fausse recherche web. Aucun réseau ni LLM réel."""

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.nodes.analyst_steps import ANALYZE_REQUEST
from app.agents.nodes.review_common import PROPOSE_REQUEST
from app.agents.nodes.review_confront import CONFRONT_REQUEST
from app.agents.nodes.scout.company import COMPANY_REQUEST
from app.agents.runtime.bus import EventBus
from app.agents.runtime.checkpointer import open_checkpointer
from app.agents.runtime.costs import ModelPrice
from app.agents.runtime.ports import AgentPorts
from app.agents.runtime.run_settings import RunSettings
from app.agents.runtime.runner import SessionRunner
from app.agents.tools.web_port import PageRead, WebHit, WebLimits, WebSearchResult
from app.db.models.agents import AgentSession
from tests.agents.graphs.council_models import CouncilModels
from tests.agents.graphs.web_support import add_users
from tests.agents.runtime.runner_helpers import TIMEOUT, all_events, get_session, wait_status
from tests.support.cv_review import REVIEW_ID, FakeCvReviewStore
from tests.support.gap import FakeGapStore, analysis_reply

START = "<<<UNTRUSTED_CONTENT"
END = "<<<END_UNTRUSTED_CONTENT>>>"
CROSS_EXAMINATION = "Cross-examination, round"
BRIEF: dict[str, Any] = {
    "summary": "Éditeur d'assistants pour le support.",
    "values": [],
    "stack": [],
    "tone": None,
}
COMPANY_URLS = [f"https://site{n}.example.org/societe" for n in range(4)]


def item(ref: str, action: str, target: str | None, after: str = "", **kw: Any) -> dict[str, Any]:
    section = {"x": "experience", "c": "skills", "f": "education", "p": "projects"}
    fields: dict[str, Any] = {
        "ref": ref,
        "section": section.get((target or "x")[:1], "summary"),
        "action": action,
        "target": target,
        "after": after,
        "reason": "Plus proche de l'offre.",
        "type": "keyword",
        "fact_ids": [],
    }
    return fields | kw


def reading(*items: dict[str, Any], **extra: Any) -> str:
    return json.dumps({"items": list(items), **extra}, ensure_ascii=False)


def stances(*entries: tuple[str, str, str | None]) -> str:
    rows = [{"ref": r, "stance": s, "after": a, "reason": "Mon avis."} for r, s, a in entries]
    return json.dumps({"stances": rows}, ensure_ascii=False)


ATS_DEFAULT = reading(
    item("a1", "rewrite", "x1a1", "Réduit les coûts de 30 % avec Python", fact_ids=["c1"]),
    item("a2", "add", "c3", "Kubernetes"),
    notes=["Sections usuelles : bien lues."],
)
RECRUITER_DEFAULT = reading(
    item("r1", "rewrite", "x1a2", "Anime l'équipe au quotidien", type="clarity"),
    strengths=["Résultat chiffré."],
    risks=["Peu de LangGraph."],
)


def reviewers(
    *,
    ats: Sequence[str] = (),
    recruiter: Sequence[str] = (),
    ats_confront: Sequence[str] = (),
    recruiter_confront: Sequence[str] = (),
) -> CouncilModels:
    """Faux modèles : les réponses du test d'abord, puis les réponses par défaut (propositions
    valables, aucune objection, une fiche entreprise, l'analyse de l'offre fictive)."""
    models = CouncilModels()
    models.when("ats_reader", PROPOSE_REQUEST, *ats, *[ATS_DEFAULT] * 10)
    models.when("recruiter", PROPOSE_REQUEST, *recruiter, *[RECRUITER_DEFAULT] * 10)
    for agent, replies in (("ats_reader", ats_confront), ("recruiter", recruiter_confront)):
        models.when(agent, CROSS_EXAMINATION, *replies, *[stances()] * 10)
    models.when("scout", COMPANY_REQUEST, *[json.dumps(BRIEF)] * 10)
    models.when("analyst", ANALYZE_REQUEST, *[analysis_reply()] * 5)
    return models


def calls(models: CouncilModels, agent: str, marker: str = "") -> list[str]:
    return [c.prompt for c in models.calls if c.agent == agent and marker in c.prompt]


def confront_calls(models: CouncilModels, round_no: int) -> list[str]:
    marker = CONFRONT_REQUEST[round_no]
    return [c.prompt for c in models.calls if marker in c.prompt]


def in_untrusted(prompt: str, phrase: str) -> bool:
    """Chaque occurrence de `phrase` est à l'intérieur d'un encadrement `untrusted`."""
    position = prompt.find(phrase)
    while position != -1:
        if prompt.rfind(START, 0, position) <= prompt.rfind(END, 0, position):
            return False
        position = prompt.find(phrase, position + 1)
    return True


@dataclass
class FakeWeb:
    """Recherche web factice : quatre résultats, pages lisibles."""

    urls: list[str] = field(default_factory=lambda: list(COMPANY_URLS))
    searches: list[str] = field(default_factory=list)
    reads: list[str] = field(default_factory=list)

    async def search(self, user_id: str, session_id: str, query: str, **_: Any) -> WebSearchResult:
        self.searches.append(query)
        hits = [WebHit("Page", url, "Extrait", "fake", None, False) for url in self.urls]
        return WebSearchResult(query, "searxng", hits)

    async def read(self, user_id: str, session_id: str, url: str) -> PageRead:
        self.reads.append(url)
        return PageRead(
            f"src-{len(self.reads)}", url, "ok", "Page", "Texte sur l'entreprise.", None, None,
            "fr", None,
        )  # fmt: skip

    async def limits(self, user_id: str) -> WebLimits:
        return WebLimits(("fr",), (), 6, 30)


class _Settings:
    async def get_run_settings(self, user_id: str) -> RunSettings:
        return RunSettings(
            session_token_cap=1_000_000,
            debate_rounds=1,
            lesson_language="fr",
            search_languages=("fr",),
            style_guide="",
        )


@dataclass
class ReviewRun:
    runner: SessionRunner
    factory: async_sessionmaker[AsyncSession]
    store: FakeCvReviewStore
    models: CouncilModels
    user_id: str
    sid: str = ""
    pending: dict[str, Any] | None = None

    async def wait_status(self, status: str) -> AgentSession:
        return await wait_status(self.factory, self.user_id, self.sid, status)

    async def question(self) -> dict[str, Any]:
        """Attend une question `cv_output` nouvelle (pas celle déjà gardée dans `pending`)."""
        old = (self.pending or {}).get("interrupt_id")
        async with asyncio.timeout(TIMEOUT):
            while True:
                row = await get_session(self.factory, self.user_id, self.sid)
                pending = row.pending_interrupt or {}
                fresh = pending.get("interrupt_id") != old
                if row.status == "waiting_user" and pending.get("kind") == "cv_output" and fresh:
                    self.pending = pending
                    return pending
                assert row.status not in ("failed", "completed"), row.error
                await asyncio.sleep(0.01)

    async def answer(self, value: Any) -> None:
        row = await get_session(self.factory, self.user_id, self.sid)
        interrupt_id = (row.pending_interrupt or {}).get("interrupt_id")
        await self.runner.resume(self.user_id, self.sid, interrupt_id, value)

    async def events(self, type_: str) -> list[dict[str, Any]]:
        events = await all_events(self.factory, self.user_id, self.sid)
        return [e.payload.model_dump() for e in events if e.type == type_]

    async def said(self) -> list[str]:
        return [e["text"] for e in await self.events("agent.message")]


type MakeReview = Callable[..., Awaitable[ReviewRun]]


@pytest.fixture
def review_store() -> FakeCvReviewStore:
    return FakeCvReviewStore()


@pytest.fixture
def review_web() -> FakeWeb:
    return FakeWeb()


@pytest.fixture
async def review_runner(
    tmp_path: Path,
    db_session_factory: async_sessionmaker[AsyncSession],
    user_id: str,
    other_user_id: str,
    review_store: FakeCvReviewStore,
    review_web: FakeWeb,
) -> AsyncIterator[MakeReview]:
    """`make(models)` lance `cv_review` sur la revue `REVIEW_ID` ; `sid=` reprend une session
    existante (nouveau « processus » : même base, même `checkpoints.db`, mêmes ports)."""
    await add_users(db_session_factory, user_id, other_user_id)
    gap = FakeGapStore()
    async with AsyncExitStack() as stack:

        async def make(models: CouncilModels | None = None, *, sid: str | None = None) -> ReviewRun:
            models = models or reviewers()
            saver = await stack.enter_async_context(open_checkpointer(tmp_path / "checkpoints.db"))
            bus = EventBus(db_session_factory)
            runner = SessionRunner(
                session_factory=db_session_factory,
                bus=bus,
                models=models,
                checkpointer=saver,
                prices={"modele-test": ModelPrice(1.0, 2.0)},
                run_settings=_Settings(),
                ports=AgentPorts(cv_review=review_store, gap=gap, web=review_web),  # type: ignore[arg-type]
            )
            stack.push_async_callback(bus.aclose)
            stack.push_async_callback(runner.shutdown)
            run = ReviewRun(runner, db_session_factory, review_store, models, user_id)
            run.sid = sid or await runner.start(user_id, "cv_review", {"review_id": REVIEW_ID})
            return run

        yield make
