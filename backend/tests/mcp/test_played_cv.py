"""Les deux captures CV utilisent les PDF du compte et le modèle du client MCP."""

import pytest
from fastapi import FastAPI

from scripts.sample_cv import make_cv_pdf
from tests.agents.runtime.runner_helpers import wait_idle
from tests.mcp.adapter_support import call, read
from tests.mcp.support import API, Mcp
from tests.support.profile import profile_reply


@pytest.mark.parametrize(
    ("launch", "arguments", "role"),
    [
        ("cv_capture_profile", {}, "archivist"),
        ("cv_capture_design", {"name": "Gabarit de test"}, "designer"),
    ],
)
async def test_played_cv_uses_existing_pdf(
    claude: Mcp, app: FastAPI, launch: str, arguments: dict[str, str], role: str
) -> None:
    file = {"file": ("exemple.pdf", make_cv_pdf(), "application/pdf")}
    doc = await claude.http.post(f"{API}/documents", files=file)
    assert doc.is_success, doc.text
    doc_id = doc.json()["document"]["id"]
    token = await claude.token(("sessions", "cv"), "write")
    key = "cv_document_id" if role == "archivist" else "document_id"
    params = {"launch": launch, "played_by": "codex", "arguments": {key: doc_id, **arguments}}
    started, error = await call(claude, token, "agents_play_start", params)
    assert not error, started
    args = {"session_id": started["data"]["session_id"]}
    runner = app.state.runtime.runner
    await wait_idle(runner, args["session_id"])
    raw = await claude.call(token, "agents_play_brief", args)
    brief, failed = read(raw)
    assert not failed and brief["data"]["agent"] == role, brief
    if role == "designer":
        images = raw.json()["result"]["content"][1:]
        assert len(images) == 1 and images[0]["type"] == "image"
        assert images[0]["mimeType"] == "image/png"
        assert images[0]["data"].startswith("iVBORw0KGgo")
        return
    submit = {**args, "step_id": brief["data"]["step_id"], "response": profile_reply()}
    result, failed = await call(claude, token, "agents_play_submit", submit)
    assert not failed, result
    await wait_idle(runner, args["session_id"])
    profile = (await claude.http.get(f"{API}/profile")).json()
    assert profile["source_document_id"] == doc_id and profile["validated"] is None
    assert profile["draft"]["status"] == "draft" and profile["draft"]["data"]["skills"]
    asked, failed = await call(
        claude, token, "cv_put_profile", {"data": profile["draft"]["data"], "base_version": 1}
    )
    assert not failed and asked["data"]["status"] == "pending_confirmation", asked
    assert (await claude.http.get(f"{API}/profile")).json()["validated"] is None
