"""Appréciations communes et trace durable d’une répétition sans candidature."""

import asyncio
import json
from collections.abc import Callable, Sequence
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from langchain_core.messages import BaseMessage
from sqlalchemy.ext.asyncio import AsyncEngine

from app.agents.runtime.structured import extract_json_object
from app.config import Settings
from tests.e2e.server import build_app
from tests.features.recruitment_process.support import GRADES, MISSING, PROJECT, seed_rehearsal

API = "/api/v1/recruitment-processes"
KINDS = ("project", "exercise", "interview")


def _reply(kind: str, grade: dict[str, Any]) -> Callable[[Sequence[BaseMessage]], str]:
    def reply(messages: Sequence[BaseMessage]) -> str:
        data = extract_json_object(str(messages[1].content))
        assert data is not None
        assert data["etape"] == kind and len(data["grille"]) == 3
        assert MISSING in data["attentes"]
        if kind == "project":
            assert data["projet_fixe"]["title"] == PROJECT
            assert "Trente échantillons" in data["projet_fixe"]["result"]
        else:
            assert data["projet_fixe"] is None
        return json.dumps(grade)

    return reply


@pytest.fixture
def app(settings: Settings, db_engine: AsyncEngine) -> FastAPI:
    scripts = [_reply(kind, grade) for kind, grade in zip(KINDS, GRADES, strict=True)]
    return build_app(settings, scripts={"verifier": scripts})


async def _progress(client: httpx.AsyncClient, path: str, expected: str | None) -> dict[str, Any]:
    async with asyncio.timeout(15):
        while True:
            row: dict[str, Any] = (await client.get(path)).json()
            if row["active_step"] == expected:
                return row
            assert row["state"] == "evaluating", row["state"]
            await asyncio.sleep(0.05)


async def test_rehearsal_resumes_after_each_review_and_keeps_missing_proofs(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    posting, project = await seed_rehearsal(app, app.state.local_user_id)
    created = await client.post(API, json={"posting_id": posting, "project_id": project})
    assert created.status_code == 201, created.text
    row = created.json()
    assert row["project"] == {"id": project, "title": PROJECT}
    assert row["missing_proofs"] == [{"requirement": MISSING, "skills": ["RAG"]}]
    frozen = row["rubric"]
    path = f"{API}/{row['id']}"
    for kind, then in zip(KINDS, ("exercise", "interview", None), strict=True):
        answered = await client.post(
            f"{path}/steps/{kind}/answers", json={"answer": f"Étape {kind}."}
        )
        assert answered.status_code == 202, answered.text
        outcome = await _progress(client, path, then)
        assert outcome["rubric"] == frozen
    assert outcome["state"] == "complete"
    assert [step["grade"] for step in outcome["steps"]] == list(GRADES)
    assert all(step["graded_at"] for step in outcome["steps"])
    duplicate = await client.post(f"{path}/steps/project/answers", json={"answer": "Double."})
    assert duplicate.status_code == 409
