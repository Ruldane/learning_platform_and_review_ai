"""Jouer le Conseil par les outils publiés, sans clé ni fournisseur réseau."""

from typing import Any

from fastapi import FastAPI
from sqlalchemy import select

from app.db.models.agents import LlmCall
from tests.agents.runtime.runner_helpers import wait_idle
from tests.mcp.adapter_support import call
from tests.mcp.support import Mcp


async def test_played_council_retries_then_waits_for_january(claude: Mcp, app: FastAPI) -> None:
    token = await claude.token(("sessions", "learning"), "write")
    registry = app.state.mcp_registry
    for name, level in [("start", 2), ("brief", 1), ("submit", 2)]:
        tool = registry.get(f"agents_play_{name}")
        assert tool and tool.level == level
    params = {
        "launch": "learning_create_goal",
        "played_by": "codex",
        "arguments": {"text": "Construire un programme de test"},
    }
    started, error = await call(claude, token, "agents_play_start", params)
    assert not error, started
    args = {"session_id": started["data"]["session_id"]}

    async def next_step() -> dict[str, Any]:
        await wait_idle(app.state.runtime.runner, args["session_id"])
        brief, failed = await call(claude, token, "agents_play_brief", args)
        assert not failed, brief
        return dict(brief["data"])

    first = await next_step()
    assert first["agent"] == "moderator" and "questions" in first["output_schema"]["properties"]
    assert any("Construire un programme de test" in m["content"] for m in first["messages"])
    submit = {**args, "step_id": first["step_id"], "response": "{}"}
    refusal, error = await call(claude, token, "agents_play_submit", submit)
    assert error and "questions" in str(refusal["data"]["error"]["details"])
    second = await next_step()
    assert second["step_id"] != first["step_id"]
    assert second["messages"][-1]["content"].startswith("Your previous reply is invalid")
    _, stale = await call(claude, token, "agents_play_submit", submit)
    assert stale
    _, error = await call(
        claude,
        token,
        "agents_play_submit",
        {**args, "step_id": second["step_id"], "response": '{"questions":[]}'},
    )
    assert not error
    human = await next_step()
    assert human["status"] == "waiting_user" and human["step_id"] is None
    _, rejected = await call(claude, token, "agents_play_submit", submit)
    assert rejected
    async with app.state.session_factory() as db:
        rows = (
            await db.scalars(select(LlmCall).where(LlmCall.session_id == args["session_id"]))
        ).all()
        assert [(r.provider, r.model, r.cost_usd) for r in rows] == [("mcp", "codex", 0)] * 2
