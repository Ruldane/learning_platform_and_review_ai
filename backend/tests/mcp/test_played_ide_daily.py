"""Parcours joués exclusivement à la demande, par leur point d'entrée public."""

import json
from dataclasses import replace
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.agents.graphs.registry import GRAPHS
from app.features.registry import MCP_FEATURES
from app.mcp.base import McpAction
from app.mcp.registry import build_registry
from app.mcp.schema import McpConfigError
from app.providers.sandbox.fake import FakeSandbox
from tests.agents.runtime.runner_helpers import wait_idle
from tests.mcp.adapter_support import call
from tests.mcp.support import API, Mcp


def test_play_alias_cannot_downgrade_existing_confirmation(app: FastAPI) -> None:
    alias = McpAction(
        "POST /programs/{program_id}/validate",
        2,
        "program_play_validation",
        launches="program_builder",
    )
    features = [
        replace(f, play_actions=(alias,)) if f.feature == "program" else f for f in MCP_FEATURES
    ]
    with pytest.raises(McpConfigError, match="level 3"):
        build_registry(features, app, {name: spec.input_model for name, spec in GRAPHS.items()})


async def launch(
    claude: Mcp, app: FastAPI, feature: str, name: str, arguments: dict[str, Any]
) -> tuple[str, str]:
    token = await claude.token(
        ("sessions", feature) if feature != "sessions" else ("sessions",), "write"
    )
    assert app.state.mcp_registry.get(name) is None
    out, failed = await call(
        claude,
        token,
        "agents_play_start",
        {"launch": name, "played_by": "codex", "arguments": arguments},
    )
    assert not failed, out
    return token, out["data"]["session_id"]


async def reply(app: FastAPI, claude: Mcp, token: str, sid: str, role: str, response: str) -> None:
    await wait_idle(app.state.runtime.runner, sid)
    args = {"session_id": sid}
    brief, failed = await call(claude, token, "agents_play_brief", args)
    assert not failed and brief["data"]["agent"] == role, brief
    assert brief["data"]["messages"][0]["role"] == "system"
    result, failed = await call(
        claude,
        token,
        "agents_play_submit",
        {**args, "step_id": brief["data"]["step_id"], "response": response},
    )
    assert not failed, result
    await wait_idle(app.state.runtime.runner, sid)


async def test_play_teacher_saves_hint(
    claude: Mcp, app: FastAPI, client: httpx.AsyncClient
) -> None:
    session = (await client.post(f"{API}/ide/sessions", json={})).json()
    token, sid = await launch(
        claude, app, "ide", "ide_teach_session", {"session_id": session["id"], "trigger": "hint"}
    )
    answer = {"kind": "hint", "text": "Regarde le nom de la variable."}
    await reply(app, claude, token, sid, "professor", json.dumps(answer))
    notes = (await client.get(f"{API}/ide/sessions/{session['id']}/notes")).json()
    assert any(n["content"] == answer["text"] and n["author"] == "professor" for n in notes)


async def test_play_exercise_saves_verified_draft(
    claude: Mcp, app: FastAPI, client: httpx.AsyncClient
) -> None:
    app.state.providers.sandbox = FakeSandbox()
    token, sid = await launch(claude, app, "ide", "ide_generate_exercise", {"topic": "Les listes"})
    draft = {
        "title": "Longueur des listes",
        "statement": "Écris une fonction qui compte les éléments d'une liste.",
        "files": {
            "main.py": "def count(xs): pass",
            "test_main.py": "from main import count\ndef test_count(): assert count([]) == 0",
        },
        "solution": {"main.py": "def count(xs): return len(xs)"},
    }
    await reply(app, claude, token, sid, "exercise_writer", json.dumps(draft))
    exercises = (await client.get(f"{API}/ide/exercises")).json()
    assert [(e["title"], e["origin"]) for e in exercises] == [(draft["title"], "generated")]


async def test_play_daily_brief_stores_advice(
    claude: Mcp, app: FastAPI, client: httpx.AsyncClient
) -> None:
    token, sid = await launch(claude, app, "brief", "brief_play_today", {})
    advice = ["Prépare ton espace de travail.", "Choisis ensuite le sujet à réviser."]
    await reply(app, claude, token, sid, "moderator", json.dumps({"sentences": advice}))
    brief = (await client.get(f"{API}/brief/today")).json()
    assert brief["session_id"] == sid and brief["advice"] == advice


async def test_play_demo_reaches_human_choice(claude: Mcp, app: FastAPI) -> None:
    token, sid = await launch(claude, app, "sessions", "graph_demo_debate", {"topic": "Les listes"})
    await reply(app, claude, token, sid, "demo_proponent", "Je propose une liste.")
    await reply(app, claude, token, sid, "demo_critic", "Quels sont ses avantages ?")
    view, failed = await call(claude, token, "agents_play_brief", {"session_id": sid})
    assert not failed and view["data"]["status"] == "waiting_user"
    assert view["data"]["step_id"] is None
