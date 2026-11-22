"""Fournisseurs scénarisés pour les routes d'écriture de leçon."""

import asyncio
from dataclasses import replace

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select

from app.db.models.memory import MemoryItem
from tests.agents.graphs.council_models import QUERY, URLS
from tests.agents.graphs.lesson_support import LessonModels
from tests.agents.graphs.web_support import document, result
from tests.support.direct import API
from tests.support.lessons import lesson_markdown, verifier_reply


def submission_text(title: str, content: str = "") -> str:
    text = lesson_markdown(title=title, urls=(URLS[0], URLS[1]))
    return text.replace("notion0", content) if content else text


@pytest.fixture
def lesson_models(
    app: FastAPI, client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> LessonModels:
    scripted = LessonModels()
    app.state.research.providers.searxng.results[QUERY] = [
        result(url, "Document de test") for url in URLS[:2]
    ]
    for url in URLS[:2]:
        app.state.research.providers.web.pages[url] = document(url)
    runner = app.state.runtime.runner
    monkeypatch.setattr(runner, "_ctx", replace(runner._ctx, models=scripted))
    return scripted


@pytest.fixture
def accept_lesson(lesson_models: LessonModels) -> LessonModels:
    lesson_models.when("verifier", "", *[verifier_reply()] * 10)
    return lesson_models


async def lesson_memory(app: FastAPI) -> list[MemoryItem]:
    async with app.state.session_factory() as db:
        return list(await db.scalars(select(MemoryItem).where(MemoryItem.kind == "lecon")))


async def wait_session(client: httpx.AsyncClient, sid: str) -> dict[str, object]:
    async with asyncio.timeout(30):
        while True:
            response = await client.get(f"{API}/sessions/{sid}")
            assert response.status_code == 200, response.text
            data = response.json()
            if data["status"] in ("completed", "failed", "cancelled"):
                return dict(data)
            await asyncio.sleep(0.02)
