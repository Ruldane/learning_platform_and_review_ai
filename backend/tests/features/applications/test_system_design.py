import json
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from langchain_core.messages import BaseMessage

from app.agents.nodes.interviewer import system_design
from app.agents.runtime.invoke import message_text
from app.agents.runtime.repositories import SessionRepository
from app.agents.tools.system_design_port import SystemDesignReview, SystemDesignSubmission
from app.features.applications.service.system_design import freeze, save_review
from tests.mcp.support import API
from tests.sessions_support import use_test_runtime, wait_status

REVIEW = {
    "criteria": {
        name: {"score": 4, "feedback": "Choix justifié dans la défense."}
        for name in ("architecture", "reliability", "scale", "tradeoffs")
    },
    "summary": "Les composants et le compromis ressortent.",
}


@pytest.fixture
def design_model(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    use_test_runtime(monkeypatch, [json.dumps(REVIEW)])
    prompts = []
    actual = system_design.structured_call

    async def observe(model: Any, schema: Any, messages: list[BaseMessage], **details: Any):
        prompts.append("\n".join(message_text(message) for message in messages))
        return await actual(model, schema, messages, **details)

    monkeypatch.setattr(system_design, "structured_call", observe)
    return prompts


async def save_rectangle(client: httpx.AsyncClient, board_id: str, label: str) -> str:
    edited = await client.post(
        f"{API}/boards/{board_id}/edits",
        json={
            "scene": {"elements": [{"id": "node", "type": "text", "text": label}]},
            "note": "Dessin",
        },
    )
    assert edited.status_code == 201, edited.text
    return str(edited.json()["id"])


@pytest.fixture(params=["System design", "Conception de systèmes"])
async def design_skill(request: pytest.FixtureRequest, client: httpx.AsyncClient) -> str:
    name: str = request.param
    if name != "System design":
        created = await client.post(f"{API}/skills", json={"name": name})
        assert created.status_code == 201, created.text
    return name


async def test_design_assesses_the_submitted_board_version_and_records_one_proof(
    design_model: list[str], client: httpx.AsyncClient, app: FastAPI, design_skill: str
) -> None:
    started = await client.post(
        f"{API}/interviews", json={"mode": "case", "duration_min": 30, "system_design": True}
    )
    assert started.status_code == 202, started.text
    session = started.json()["session_id"]
    interview = started.json()["interview_id"]
    incoming = await wait_status(client, session, "waiting_user")
    path = f"{API}/interviews/{interview}/design"
    assignment = (await client.get(path)).json()
    assert assignment["subject"]["requirements"]
    first = await save_rectangle(client, assignment["board"]["id"], "File de travaux")
    latest = await save_rectangle(client, first, "Modification plus récente")
    assert (await client.get(path)).json()["board"]["id"] == latest
    submitted = await client.post(
        f"{API}/sessions/{session}/resume",
        json={
            "interrupt_id": incoming["pending_interrupt"]["interrupt_id"],
            "value": {"board_id": first, "defense": "La file absorbe les pointes de charge."},
        },
    )
    assert submitted.status_code == 202, submitted.text
    await wait_status(client, session, "completed")
    result = (await client.get(path)).json()
    assert result["board"]["id"] == first
    assert result["review"]["summary"] == REVIEW["summary"]
    assert result["proof_saved"] is True
    assert len(design_model) == 1
    assert "File de travaux" in design_model[0]
    assert "Modification plus récente" not in design_model[0]
    await save_review(
        app.state.career.applications,
        app.state.local_user_id,
        session,
        interview,
        SystemDesignReview.model_validate(REVIEW),
    )
    graph = (await client.get(f"{API}/skills/graph")).json()
    [skill] = [node for node in graph["nodes"] if node["name"] == design_skill]
    assert skill["level"] == "in_progress"
    detail = (await client.get(f"{API}/skills/{skill['id']}")).json()
    [proof] = [item for item in detail["evidence"] if item["kind"] == "system_design"]
    assert proof["label"] == "Passed system design interview"


async def test_cancelled_session_cannot_save_a_design_review(
    design_model: list[str], client: httpx.AsyncClient, app: FastAPI
) -> None:
    started = await client.post(
        f"{API}/interviews", json={"mode": "case", "duration_min": 30, "system_design": True}
    )
    assert started.status_code == 202, started.text
    session = started.json()["session_id"]
    interview = started.json()["interview_id"]
    await wait_status(client, session, "waiting_user")
    path = f"{API}/interviews/{interview}/design"
    assignment = (await client.get(path)).json()
    version = await save_rectangle(client, assignment["board"]["id"], "File de travaux")
    runtime = app.state.career.applications
    user = app.state.local_user_id
    await freeze(
        runtime,
        user,
        session,
        interview,
        SystemDesignSubmission(board_id=version, defense="La file absorbe les pointes."),
    )
    async with runtime.session_factory() as db:
        assert await SessionRepository(db, user).transition(
            session, from_={"waiting_user"}, to="cancelled", pending_interrupt=None
        )
        await db.commit()
    await save_review(runtime, user, session, interview, SystemDesignReview.model_validate(REVIEW))
    final = (await client.get(path)).json()
    assert final["review"] is None
    assert final["proof_saved"] is False
