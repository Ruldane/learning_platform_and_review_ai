"""Le rapport évalué ne donne qu’une preuve, et seulement après le diagnostic."""

import asyncio
import json

import httpx
import pytest
from fastapi import FastAPI
from langchain_core.language_models import BaseChatModel
from sqlalchemy import select

from app.agents.tools.oncall_port import ReviewScore
from app.db.models.skills import UserSkill
from app.features.oncall.service.report import AgentOncallStore
from app.providers.llm.base import Tier
from app.providers.llm.fake import FakeLlmProvider
from app.providers.sandbox.fake import FakeSandbox
from tests.features.oncall.test_incidents import GOOD, IDE, ROOT, alerted, opened

SCORE = ReviewScore(
    diagnosis=4, evidence=4, correction=4, prevention=4, feedback="Raisonnement étayé."
)


class ReviewModels:
    def __init__(self) -> None:
        self.provider = FakeLlmProvider([json.dumps(SCORE.model_dump())])

    async def get_chat_model(
        self, user_id: str, tier: Tier, agent: str | None = None
    ) -> BaseChatModel:
        return self.provider.build("modèle-fictif", "clé-fictive")


@pytest.fixture
def review_models(app: FastAPI) -> ReviewModels:
    model = ReviewModels()
    app.state.injected_chat_models = model
    return model


async def test_review_runs_through_the_agent_port_and_records_one_proof(
    review_models: ReviewModels,
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    app.state.providers.sandbox = FakeSandbox({"*": GOOD})
    incident = await opened(client)
    root = f"{ROOT}/{incident['id']}"
    raised = await alerted(client, root)
    await client.post(f"{root}/events/{raised['events'][-1]['id']}/observe")
    await client.post(f"{root}/diagnostic")
    assert (await client.get(root)).json()["diagnostic"]["state"] == "passed"
    report = {
        "text": "La latence est devenue anormale. J’ai réglé le service et contrôlé son seuil."
    }
    started = await client.post(f"{root}/report", json=report)
    assert started.status_code == 202, started.text
    session_id = started.json()["session_id"]
    async with asyncio.timeout(8):
        while (result := (await client.get(root)).json())["review_state"] == "running":
            await asyncio.sleep(0.05)
    assert result["proof_recorded"] and result["verdict"]["feedback"] == SCORE.feedback
    assert len(review_models.provider.received) == 1

    factory = app.state.session_factory
    owner = app.state.local_user_id
    replay = await AgentOncallStore(factory).record(owner, incident["id"], session_id, SCORE)
    assert replay is True
    async with factory() as db:
        rows = (await db.execute(select(UserSkill).where(UserSkill.user_id == owner))).scalars()
        proofs = [
            item
            for row in rows
            for item in row.evidence
            if item.get("ref_id") == incident["ide_session_id"]
        ]
    assert len(proofs) == 1 and proofs[0]["kind"] == "ide"


async def _reportable(client: httpx.AsyncClient, app: FastAPI) -> tuple[str, dict]:
    app.state.providers.sandbox = FakeSandbox({"*": GOOD})
    incident = await opened(client)
    root = f"{ROOT}/{incident['id']}"
    raised = await alerted(client, root)
    await client.post(f"{root}/diagnostic")
    assert (await client.get(root)).json()["diagnostic"]["state"] == "passed"
    return root, raised


async def test_report_requires_a_consulted_event(client: httpx.AsyncClient, app: FastAPI) -> None:
    root, _ = await _reportable(client, app)
    report = {"text": "Le service est réparé après contrôle."}
    refused = await client.post(f"{root}/report", json=report)
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "incident_observation_required"


class PausedReviewModels(ReviewModels):
    def __init__(self) -> None:
        super().__init__()
        self.started = asyncio.Event()
        self.finish = asyncio.Event()

    async def get_chat_model(
        self, user_id: str, tier: Tier, agent: str | None = None
    ) -> BaseChatModel:
        self.started.set()
        await self.finish.wait()
        return await super().get_chat_model(user_id, tier, agent)


@pytest.fixture
def paused_models(app: FastAPI) -> PausedReviewModels:
    models = PausedReviewModels()
    app.state.injected_chat_models = models
    return models


async def test_new_diagnostic_cannot_validate_an_older_review(
    paused_models: PausedReviewModels, client: httpx.AsyncClient, app: FastAPI
) -> None:
    root, raised = await _reportable(client, app)
    await client.post(f"{root}/events/{raised['events'][-1]['id']}/observe")
    report = {"text": "La cause a été confirmée et la première correction vérifiée."}
    started = await client.post(f"{root}/report", json=report)
    assert started.status_code == 202
    try:
        async with asyncio.timeout(8):
            await paused_models.started.wait()
        project = f"{IDE}/{raised['ide_session_id']}"
        source = (await client.get(project)).json()["files"]
        source["service.py"] += "\n# Second état du service\n"
        assert (await client.put(f"{project}/files", json={"files": source})).is_success
        await client.post(f"{root}/diagnostic")
        assert (await client.get(root)).json()["diagnostic"]["state"] == "passed"
    finally:
        paused_models.finish.set()
    async with asyncio.timeout(8):
        while (result := (await client.get(root)).json())["review_state"] == "running":
            await asyncio.sleep(0.05)
    assert result["verdict"] is not None and not result["proof_recorded"]
