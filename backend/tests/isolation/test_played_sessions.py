import json

import pytest
from fastapi import FastAPI

from tests.features.auth.support import CAMILLE, DOMINIQUE
from tests.isolation.conftest import Browser
from tests.mcp.adapter_support import call
from tests.mcp.support import Mcp


@pytest.mark.parametrize("route", ["agents_play_brief", "agents_play_submit"])
async def test_foreign_session_is_invisible(
    google_client_factory: Browser, google_app: FastAPI, route: str
) -> None:
    alice = Mcp(await google_client_factory(CAMILLE))
    bob = Mcp(await google_client_factory(DOMINIQUE))
    token_a = await alice.token(("sessions", "learning"), "write")
    token_b = await bob.token(("sessions", "learning"), "write")
    launch = {
        "launch": "learning_create_goal",
        "arguments": {"text": "Programme privé de Camille"},
        "played_by": "codex",
    }
    result, error = await call(alice, token_a, "agents_play_start", launch)
    assert not error
    sid = result["data"]["session_id"]
    params = {"session_id": sid}
    if route == "agents_play_submit":
        params.update(step_id="0" * 36, response="{}")
    result, error = await call(bob, token_b, route, params)
    assert error and result["data"]["error"]["code"] == "session_not_found"
    assert "Programme privé" not in json.dumps(result, ensure_ascii=False)
