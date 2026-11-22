"""La note repose sur la remise figée et ne donne qu'une preuve."""

import asyncio
from datetime import timedelta

import httpx
import pytest
from fastapi import FastAPI
from langchain_core.language_models import BaseChatModel
from sqlalchemy import select

from app.core.played import run_source
from app.db.base import utcnow
from app.db.models.skills import UserSkill
from app.providers.llm.base import Tier
from app.providers.llm.fake import FakeLlmProvider
from app.providers.sandbox.base import SandboxProgress
from app.providers.sandbox.fake import FakeSandbox
from tests.support.boss import CORRECTION, OUTPUT, RUBRIC, completed_program


class DelayedSandbox(FakeSandbox):
    def __init__(self) -> None:
        super().__init__({"*": OUTPUT})
        self.finish = asyncio.Event()

    async def poll(self, run_id: str, offset: int) -> SandboxProgress:
        if self.jobs:
            await self.finish.wait()
        return await super().poll(run_id, offset)


class ReviewModels:
    def __init__(self) -> None:
        self.provider = FakeLlmProvider([RUBRIC])
        self.sources: list[tuple[str | None, str | None]] = []

    async def get_chat_model(
        self, user_id: str, tier: Tier, agent: str | None = None
    ) -> BaseChatModel:
        self.sources.append(run_source(user_id))
        assert agent == "boss_reviewer"
        return self.provider.build("boss-scripté", "clé-fictive")


@pytest.fixture
def review_models(app: FastAPI) -> ReviewModels:
    models = ReviewModels()
    app.state.injected_chat_models = models
    return models


async def test_review_grades_frozen_files_once(
    review_models: ReviewModels, app: FastAPI, client: httpx.AsyncClient
) -> None:
    now = utcnow()
    app.state.boss_clock = lambda: now
    sandbox = DelayedSandbox()
    app.state.providers.sandbox = sandbox
    route = f"/api/v1/boss/programs/{await completed_program(app)}"
    attempt = (await client.post(route)).json()
    project = f"/api/v1/ide/sessions/{attempt['ide_session_id']}/files"
    files = {"service.py": CORRECTION, "helpers.py": "# Projet multifichier\n"}
    assert (await client.put(project, json={"files": files})).is_success
    now += timedelta(minutes=11)
    submit = f"{route}/submit"
    result = await client.post(submit, headers={"X-Tremplin-Run": "anthropic"})
    assert result.status_code == 202, result.text
    try:
        assert (await client.post(submit)).json() == result.json()
        edited = {"service.py": "# Retouche après remise\n"}
        assert (await client.put(project, json={"files": edited})).is_success
    finally:
        sandbox.finish.set()
    async with asyncio.timeout(10):
        while (view := (await client.get(route)).json()["attempt"])["state"] == "reviewing":
            await asyncio.sleep(0.05)
    assert view["state"] == "graded" and view["proof_recorded"]
    assert view["grade"]["functionality"] == 10 and view["grade"]["total"] == 18
    assert len(view["grade"]["diagnostic"]["checks"]) == 4
    assert (await client.post(submit)).json() == result.json()
    assert len(review_models.provider.received) == 1
    assert review_models.sources == [(None, "openai")]
    [job] = sandbox.jobs
    assert {name: job.files[name] for name in files} == files
    async with app.state.session_factory() as db:
        stmt = select(UserSkill).where(UserSkill.user_id == app.state.local_user_id)
        rows = await db.scalars(stmt)
        proofs = [
            e for row in rows for e in row.evidence if e["ref_id"] == attempt["ide_session_id"]
        ]
        assert len(proofs) == 1
