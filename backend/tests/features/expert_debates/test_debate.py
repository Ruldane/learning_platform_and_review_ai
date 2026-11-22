"""Les citations sont bornées au catalogue de chaque prise de parole."""

import asyncio
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from app.core.providers import ResearchProviders
from app.providers.search.fake import FakeSearch
from tests.e2e.scripted_models import ScriptedModels
from tests.support.expert_debates import (
    JUDGMENT,
    METHOD,
    PRACTICE,
    QUESTION,
    expert_scripts,
    script_expert_sources,
)
from tests.support.memory import FakeWebReader

PATH = "/api/v1/expert-debates"


def _setup(app: FastAPI, research_providers: ResearchProviders, models: ScriptedModels) -> None:
    web, search = research_providers.web, research_providers.searxng
    assert isinstance(web, FakeWebReader) and isinstance(search, FakeSearch)
    script_expert_sources(web, search)
    app.state.injected_chat_models = models


@pytest.fixture
def scripted(app: FastAPI, research_providers: ResearchProviders) -> ScriptedModels:
    models = ScriptedModels(expert_scripts())
    _setup(app, research_providers, models)
    return models


async def test_debate_cites_each_expert_and_reopens_user_judgment(
    scripted: ScriptedModels, client: httpx.AsyncClient
) -> None:
    body = {"request_id": str(uuid4()), "question": QUESTION}
    opened = await client.post(PATH, json=body)
    assert opened.status_code == 202, opened.text
    assert (await client.post(PATH, json=body)).json() == opened.json()
    route = f"{PATH}/{opened.json()['debate_id']}"
    async with asyncio.timeout(10):
        while (debate := (await client.get(route)).json())["status"] == "running":
            await asyncio.sleep(0.05)
    assert debate["status"] == "completed" and debate["question"] == QUESTION
    talks = debate["speeches"]
    assert [talk["role"] for talk in talks] == ["researcher", "practitioner", "skeptic"]
    assert [[source["url"] for source in talk["citations"]] for talk in talks] == [
        [METHOD],
        [PRACTICE],
        [METHOD],
    ]
    assert "[99]" not in talks[-1]["text"] and "99" not in str(talks[-1]["citations"])
    assert scripted.served == {"scout": 1, "practitioner": 1, "skeptic": 1}
    judgment = await client.put(f"{route}/judgment", json={"text": JUDGMENT})
    assert judgment.status_code == 200
    assert (await client.get(route)).json()["judgment"] == JUDGMENT
    assert (await client.get(PATH)).json()[0]["id"] == opened.json()["debate_id"]


class _PauseBeforePractitioner(ScriptedModels):
    def __init__(self) -> None:
        super().__init__(expert_scripts())
        self.entered = asyncio.Event()

    async def wait(self, agent: str) -> None:
        if agent == "practitioner" and not self.entered.is_set():
            self.entered.set()
            await asyncio.Event().wait()
        await super().wait(agent)


@pytest.fixture
def paused_script(app: FastAPI, research_providers: ResearchProviders) -> _PauseBeforePractitioner:
    models = _PauseBeforePractitioner()
    _setup(app, research_providers, models)
    return models


async def test_pause_resumes_between_experts_without_repeating_the_opening(
    paused_script: _PauseBeforePractitioner,
    research_providers: ResearchProviders,
    client: httpx.AsyncClient,
) -> None:
    opened = await client.post(PATH, json={"request_id": str(uuid4()), "question": QUESTION})
    assert opened.status_code == 202
    data = opened.json()
    route, session = f"{PATH}/{data['debate_id']}", f"/api/v1/sessions/{data['session_id']}"
    await asyncio.wait_for(paused_script.entered.wait(), timeout=10)
    assert (await client.post(f"{session}/pause")).json()["status"] == "paused"
    assert (await client.get(route)).json()["speeches"] == []
    assert (await client.put(f"{route}/judgment", json={"text": JUDGMENT})).status_code == 409
    assert paused_script.served == {"scout": 1}
    assert (await client.post(f"{session}/resume", json={})).status_code == 202
    async with asyncio.timeout(10):
        while (debate := (await client.get(route)).json())["status"] == "running":
            await asyncio.sleep(0.05)
    assert debate["status"] == "completed"
    assert [speech["citations"][0]["url"] for speech in debate["speeches"]] == [
        METHOD,
        PRACTICE,
        METHOD,
    ]
    assert paused_script.served == {"scout": 1, "practitioner": 1, "skeptic": 1}
    assert isinstance(research_providers.searxng, FakeSearch)
    assert len(research_providers.searxng.calls) == 1
