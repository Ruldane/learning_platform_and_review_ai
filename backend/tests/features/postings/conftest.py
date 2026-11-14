"""Matériel des tests des offres (D122) : l'app réelle avec un lanceur factice (aucune session ne
tourne, aucun LLM), le faux lecteur web de la suite (aucun réseau), le vrai port de l'écart
(`AgentGapStore`) sur la vraie mémoire (`HashingEmbedder`, Qdrant en mémoire)."""

from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import func, select

from app.agents.tools.gap_port import SkillMatch
from app.agents.tools.posting_schema import PostingAnalysis
from app.core.providers import MemoryProviders
from app.db.models.postings import JobPosting
from app.features.memory.service.runtime import MemoryRuntime, memory_runtime
from app.features.postings.service.agent_store import AgentGapStore
from app.providers.web.base import WebDocument
from scripts.sample_posting import POSTING_TEXT
from tests.features.lessons.conftest import RecordingLauncher
from tests.features.program.support import Factory
from tests.support.gap import MATCHES, analysis_data
from tests.support.memory import FakeWebReader

API = "/api/v1"
LINK = "https://jobs.exemple.org/offres/ai-product-engineer"
ME = "moi"


def analysis(**over: Any) -> PostingAnalysis:
    return PostingAnalysis.model_validate(analysis_data(**over))


def page(url: str, text: str = POSTING_TEXT) -> WebDocument:
    return WebDocument(url, "Offre", text, None, None, "fr", None)


@pytest.fixture
def launcher_spy(client: httpx.AsyncClient, app: FastAPI) -> RecordingLauncher:
    """Remplace le lanceur des offres, une fois l'app démarrée (`client`)."""
    spy = RecordingLauncher(app.state.session_factory)
    app.state.career.postings.launcher = spy
    return spy


@pytest.fixture
def fake_reader(memory_providers: MemoryProviders) -> FakeWebReader:
    reader = memory_providers.web
    assert isinstance(reader, FakeWebReader)
    return reader


async def count_postings(factory: Factory) -> int:
    async with factory() as db:
        return int((await db.execute(select(func.count()).select_from(JobPosting))).scalar_one())


async def add_posting(
    factory: Factory, user_id: str = ME, *, text: str = POSTING_TEXT, **fields: Any
) -> str:
    async with factory() as db:
        row = JobPosting(
            user_id=user_id,
            source="url" if fields.get("url_norm") else "text",
            text=text,
            text_hash=fields.pop("text_hash", f"h-{len(text)}-{id(fields)}"),
            status=fields.pop("status", "analyzing"),
            **fields,
        )
        db.add(row)
        await db.commit()
        return row.id


async def fresh(factory: Factory, posting_id: str) -> JobPosting:
    async with factory() as db:
        row = await db.get(JobPosting, posting_id)
        assert row is not None
        return row


@pytest.fixture
async def memory(
    db_session_factory: Factory, memory_providers: MemoryProviders
) -> AsyncIterator[MemoryRuntime]:
    async with memory_runtime(db_session_factory, memory_providers) as runtime:
        yield runtime


@pytest.fixture
def store(db_session_factory: Factory, memory: MemoryRuntime) -> AgentGapStore:
    return AgentGapStore(db_session_factory, memory)


async def post_link(client: httpx.AsyncClient, url: str = LINK) -> httpx.Response:
    return await client.post(f"{API}/postings", json={"url": url})


async def analyzed_posting(
    client: httpx.AsyncClient, app: FastAPI, text: str = POSTING_TEXT, **over: Any
) -> str:
    """Une offre ajoutée par la route puis analysée par le vrai port, écart rangé avec les
    rattachements de `tests.support.gap.MATCHES` (le lanceur des offres doit être factice)."""
    r = await client.post(f"{API}/postings", json={"text": text})
    assert r.status_code == 201, r.text
    posting_id, session = r.json()["posting"]["id"], r.json()["session_id"]
    store, user = app.state.career.gap, app.state.local_user_id
    await store.save_analysis(user, session, posting_id, analysis(**over))
    found = [SkillMatch(need=need, known=known) for need, known in MATCHES.items()]
    await store.save_gap(user, session, posting_id, found)
    return str(posting_id)
