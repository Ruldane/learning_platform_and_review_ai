"""Contrôles communs à tout parcours joué, au point d'entrée MCP."""

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import FastAPI
from sqlalchemy import func, select

from app.db.models.agents import AgentSession, LlmCall
from app.features.sessions.service import expire_steps
from tests.agents.runtime.runner_helpers import wait_idle
from tests.mcp.adapter_support import call
from tests.mcp.support import Mcp

LAUNCH = {
    "launch": "learning_create_goal",
    "played_by": "claude-code",
    "arguments": {"text": "Apprendre à créer un programme"},
}


async def opened(claude: Mcp, app: FastAPI) -> tuple[str, dict[str, Any]]:
    token = await claude.token(("sessions", "learning"), "write")
    result, error = await call(claude, token, "agents_play_start", LAUNCH)
    assert not error, result
    sid = result["data"]["session_id"]
    await wait_idle(app.state.runtime.runner, sid)
    result, error = await call(claude, token, "agents_play_brief", {"session_id": sid})
    assert not error and result["data"]["step_id"]
    return token, result["data"]


async def test_expired_step_is_closed_and_never_billed(claude: Mcp, app: FastAPI) -> None:
    token, brief = await opened(claude, app)
    expires = datetime.fromisoformat(brief["expires_at"])
    assert timedelta(hours=23) < expires - datetime.now(UTC) <= timedelta(days=1)
    await expire_steps(app.state.session_factory, expires + timedelta(seconds=1))
    params = {"session_id": brief["session_id"]}
    result, error = await call(claude, token, "agents_play_brief", params)
    assert not error and result["data"]["status"] == "expired"
    assert result["data"]["step_id"] is None and not result["data"]["messages"]
    answer = {**params, "step_id": brief["step_id"], "response": '{"questions":[]}'}
    assert (await call(claude, token, "agents_play_submit", answer))[1]
    async with app.state.session_factory() as db:
        assert await db.scalar(select(func.count()).select_from(LlmCall)) == 0


async def test_scope_and_read_mode_apply_to_every_step(claude: Mcp, app: FastAPI) -> None:
    token, brief = await opened(claude, app)
    sid = {"session_id": brief["session_id"]}
    answer = {**sid, "step_id": brief["step_id"], "response": '{"questions":[]}'}
    limited = await claude.token(("sessions",), "write")
    reader = await claude.token(("sessions", "learning"), "read")
    for name, params in [("start", LAUNCH), ("brief", sid), ("submit", answer)]:
        refusal, error = await call(claude, limited, f"agents_play_{name}", params)
        assert error and LAUNCH["arguments"]["text"] not in json.dumps(refusal, ensure_ascii=False)
    assert not (await call(claude, reader, "agents_play_brief", sid))[1]
    rejected = await claude.call(reader, "agents_play_submit", answer)
    assert rejected.status_code == 403
    assert rejected.json()["error"]["code"] == "write_not_allowed"
    assert not (await call(claude, token, "sessions_cancel_session", sid))[1]
    assert (await call(claude, token, "agents_play_submit", answer))[1]


async def test_launch_limit_applies_to_played_routes(claude: Mcp, app: FastAPI) -> None:
    app.state.runtime.runner.launch_quota.limit = 1
    token, _ = await opened(claude, app)
    result, error = await call(claude, token, "agents_play_start", LAUNCH)
    assert error and result["data"]["error"]["code"] == "mcp_graph_quota"
    async with app.state.session_factory() as db:
        assert await db.scalar(select(func.count()).select_from(AgentSession)) == 1
