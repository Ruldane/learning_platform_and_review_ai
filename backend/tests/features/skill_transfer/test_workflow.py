"""Exercice inédit à l’échéance et appréciation rattachée à la preuve d’origine."""

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from app.config import Settings
from app.core.skills import evidence
from app.features.skill_transfer.router import clock
from app.features.skills.service import SkillsService
from tests.e2e.server import build_app
from tests.e2e.skill_transfer import ASSESSMENT, EXERCISE
from tests.features.quiz.conftest import seed
from tests.features.quiz.support import ready_quiz
from tests.support.quiz import question

API = "/api/v1/skill-transfers"


@pytest.fixture
def app(settings: Settings, db_engine: AsyncEngine) -> FastAPI:
    reused = {**EXERCISE, "prompt": question("mcq", 1)["prompt"]}
    return build_app(
        settings,
        scripts={"verifier": [json.dumps(item) for item in (reused, EXERCISE, ASSESSMENT)]},
    )


async def _control_of_quiz(app: FastAPI, client: httpx.AsyncClient) -> tuple[str, str]:
    seeded = await seed(app)
    quiz_id = await ready_quiz(seeded)
    async with app.state.session_factory() as db:
        service = SkillsService(db, seeded.user_id)
        await service.raise_levels(
            ["pandas"], "valide", evidence("quiz", quiz_id, "Quiz de pandas", datetime.now(UTC))
        )
        skill_id = await service.skill_id_for("pandas")
        await db.commit()
    settings = (await client.get("/api/v1/settings")).json()
    assert (
        await client.put("/api/v1/settings", json={**settings, "timezone": "America/Montreal"})
    ).is_success
    [proof] = (await client.get(f"{API}/proofs", params={"skill_id": skill_id})).json()
    created = await client.post(
        API, json={"skill_id": skill_id, "proof_id": proof["id"], "due_on": "2026-11-22"}
    )
    assert created.status_code == 201, created.text
    return f"{API}/{created.json()['id']}", str(skill_id)


async def _wait_for(client: httpx.AsyncClient, path: str, **fields: str) -> dict[str, Any]:
    async with asyncio.timeout(15):
        while True:
            response = await client.get(path)
            assert response.status_code == 200
            row: dict[str, Any] = response.json()
            if all(row[key] == value for key, value in fields.items()):
                return row
            await asyncio.sleep(0.05)


async def test_rejects_reused_quiz_then_keeps_the_original_proof(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    app.dependency_overrides[clock] = lambda: datetime(2026, 11, 22, 1, tzinfo=UTC)
    path, skill_id = await _control_of_quiz(app, client)
    before = (await client.get(f"/api/v1/skills/{skill_id}")).json()
    assert (await client.get(path)).json()["available"] is False
    assert (await client.post(f"{path}/prepare")).json()["error"][
        "code"
    ] == "skill_transfer_not_due"

    app.dependency_overrides[clock] = lambda: datetime(2026, 11, 22, 12, tzinfo=UTC)
    assert (await client.get(path)).json()["available"] is True
    assert (await client.post(f"{path}/prepare")).status_code == 202
    refused = await _wait_for(client, path, retry="prepare")
    assert refused["exercise"] is None

    assert (await client.post(f"{path}/prepare")).status_code == 202
    ready = await _wait_for(client, path, stage="ready")
    assert ready["exercise"] == {"title": EXERCISE["title"], "prompt": EXERCISE["prompt"]}
    assert ready["assessment"] is None
    answer = {"answer": "Je relis le reçu associé à l’identifiant stable."}
    assert (await client.post(f"{path}/answer", json=answer)).status_code == 202
    done = await _wait_for(client, path, stage="complete")
    assert done["assessment"]["verdict"] == "needs_review"
    assert done["assessment"]["assessed_at"]
    assert (await client.post(f"{path}/answer", json=answer)).status_code == 409
    [entry] = (await client.get(API, params={"skill_id": skill_id})).json()
    assert entry["assessment"] == done["assessment"]
    after = (await client.get(f"/api/v1/skills/{skill_id}")).json()
    assert (after["level"], after["evidence"]) == (before["level"], before["evidence"])
