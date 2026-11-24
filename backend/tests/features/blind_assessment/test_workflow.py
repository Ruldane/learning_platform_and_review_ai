"""Ordre masqué, contenu réellement évalué et liens révélés avec le verdict."""

import asyncio
import json
from collections.abc import Sequence

import httpx
import pytest
from fastapi import FastAPI
from langchain_core.messages import BaseMessage
from sqlalchemy.ext.asyncio import AsyncEngine

from app.config import Settings
from app.features.blind_assessment.service import comparisons
from tests.e2e.server import build_app
from tests.features.blind_assessment.support import (
    FIRST,
    OWNER_MAIL,
    OWNER_NAME,
    OWNER_PHONE,
    SECOND,
    pdf_version,
    seed_versions,
)

API = "/api/v1/blind-assessments"
GRADE = {
    "scores_a": [4, 4, 3],
    "scores_b": [2, 2, 1],
    "feedback": "Le texte A précise le volume et la manière de suivre les délais.",
}


def blind_reply(messages: Sequence[BaseMessage]) -> str:
    prompt = str(messages[1].content)
    assert OWNER_NAME not in prompt and "Helene" not in prompt
    assert OWNER_MAIL not in prompt and OWNER_PHONE not in prompt
    assert "cv-1.pdf" not in prompt and "cv-2.pdf" not in prompt and "CV n°" not in prompt
    assert '"id"' not in prompt
    assert FIRST in prompt and SECOND in prompt
    assert prompt.index(SECOND) < prompt.index(FIRST)
    assert "Readability" in prompt and "The sections and their order guide the reader." in prompt
    return json.dumps(GRADE)


@pytest.fixture
def app(settings: Settings, db_engine: AsyncEngine) -> FastAPI:
    return build_app(settings, scripts={"verifier": [blind_reply]})


async def _wait_for_result(client: httpx.AsyncClient, path: str) -> dict:
    async with asyncio.timeout(15):
        while True:
            row = (await client.get(path)).json()
            if row["stage"] == "complete":
                return row
            assert row["stage"] == "evaluating", row
            await asyncio.sleep(0.05)


async def test_frozen_order_and_rubric_are_evaluated_before_links_are_revealed(
    app: FastAPI, client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(comparisons, "randbelow", lambda _: 1)
    first, second = await seed_versions(app, app.state.local_user_id)
    body = {"first_version_id": first, "second_version_id": second, "rubric": "clarity"}
    created = await client.post(API, json=body)
    assert created.status_code == 201, created.text
    frozen = created.json()["rubric"]
    path = f"{API}/{created.json()['id']}"
    hidden = await client.get(path)
    assert first not in hidden.text and second not in hidden.text
    assert hidden.json()["result"] is None
    assert (await client.post(f"{path}/evaluate")).status_code == 202
    done = await _wait_for_result(client, path)
    assert done["rubric"] == frozen
    result = done["result"]
    assert result["verdict"] == "a"
    assert result["source_a"]["id"] == second
    assert result["source_b"]["id"] == first
    assert (await client.get(result["source_a"]["url"])).content == pdf_version(2)
    assert (await client.get(result["source_b"]["url"])).content == pdf_version(1)
    assert (await client.post(f"{path}/evaluate")).status_code == 409
