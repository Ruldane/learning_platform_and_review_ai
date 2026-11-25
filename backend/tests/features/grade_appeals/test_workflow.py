"""L’original et les deux justifications demeurent après le choix de January."""

import asyncio
import json
from collections.abc import Sequence
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from langchain_core.messages import BaseMessage
from sqlalchemy.ext.asyncio import AsyncEngine

from app.agents.runtime.structured import extract_json_object
from app.config import Settings
from app.db.models.daily import Project
from tests.e2e.server import build_app
from tests.features.grade_appeals.support import (
    CRITERION,
    DESCRIPTION,
    ORIGINAL,
    REASON,
    SECOND,
    seed_reviewed_project,
)

API = "/api/v1/grade-appeals"


def second_reader(messages: Sequence[BaseMessage]) -> str:
    payload = extract_json_object(str(messages[1].content))
    assert payload == {
        "criterion": CRITERION,
        "frozen_submission": DESCRIPTION,
        "appeal_reason": REASON,
    }
    return json.dumps({"met": True, "comment": SECOND})


@pytest.fixture
def app(settings: Settings, db_engine: AsyncEngine) -> FastAPI:
    return build_app(settings, scripts={"verifier": [second_reader]})


async def _result(client: httpx.AsyncClient, path: str) -> dict[str, Any]:
    async with asyncio.timeout(15):
        while True:
            payload: dict[str, Any] = (await client.get(path)).json()
            if payload["state"] == "ready":
                return payload
            assert payload["state"] == "reviewing", payload["state"]
            await asyncio.sleep(0.05)


async def test_second_reading_uses_frozen_submission_and_final_choice_is_explicit(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    project = await seed_reviewed_project(app, app.state.local_user_id)
    created = await client.post(
        API, json={"project_id": project, "criterion_index": 1, "reason": REASON}
    )
    assert created.status_code == 201, created.text
    path = f"{API}/{created.json()['id']}"
    assert created.json()["source"]["criterion"]["original_comment"] == ORIGINAL
    async with app.state.session_factory() as db:
        original = await db.get(Project, project)
        assert original is not None
        original.submissions = [
            {**original.submissions[0], "description": "Texte modifié ensuite."}
        ]
        await db.commit()
    assert (await client.post(f"{path}/review")).status_code == 202
    reviewed = await _result(client, path)
    assert reviewed["source"]["submission"] == DESCRIPTION
    assert not reviewed["source"]["criterion"]["original_met"]
    assert reviewed["second"] == {"met": True, "comment": SECOND}
    assert reviewed["decision"] is None

    chosen = {"decision": "accept_second"}
    decided = await client.post(f"{path}/decision", json=chosen)
    assert decided.status_code == 200
    assert decided.json()["state"] == "decided" and decided.json()["decided_at"]
    assert (await client.post(f"{path}/decision", json=chosen)).json() == decided.json()
    conflict = await client.post(f"{path}/decision", json={"decision": "keep_original"})
    assert conflict.status_code == 409
    detail = (await client.get(f"/api/v1/projects/{project}")).json()
    assert detail["evaluation"]["results"][0]["met"] is False
