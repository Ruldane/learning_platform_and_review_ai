"""La Fabrique vérifie aussi les brouillons soumis par une session jouée."""

from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from tests.agents.runtime.runner_helpers import wait_idle
from tests.mcp.adapter_support import call
from tests.mcp.support import API, Mcp
from tests.support.direct import Seed
from tests.support.lesson_verification import submission_text, wait_session

TITLE = "Module Bases"


async def submit(
    claude: Mcp, launch: str, arguments: dict[str, Any]
) -> tuple[dict[str, Any], bool]:
    token = await claude.token(("sessions", "lessons"), "write")
    return await call(
        claude,
        token,
        "agents_play_start",
        {"launch": launch, "played_by": "codex", "arguments": arguments},
    )


async def assert_played(client: httpx.AsyncClient, app: FastAPI, sid: str) -> None:
    await wait_idle(app.state.runtime.runner, sid)
    session = (await client.get(f"{API}/sessions/{sid}")).json()
    assert session["graph"] == "lesson_factory"
    assert session["played_by"] == "codex"
    assert session["status"] == "waiting_user"


async def test_codex_can_verify_a_submitted_chapter(
    claude: Mcp,
    app: FastAPI,
    client: httpx.AsyncClient,
    drafted: Seed,
) -> None:
    started, failed = await submit(
        claude,
        "lessons_write_lesson",
        {"module_id": drafted.modules[0], "markdown": submission_text(TITLE)},
    )
    assert not failed, started
    await assert_played(client, app, started["data"]["session_id"])


@pytest.mark.usefixtures("accept_lesson")
async def test_played_patch_requires_content_before_attaching_resources(
    claude: Mcp,
    app: FastAPI,
    client: httpx.AsyncClient,
    drafted: Seed,
) -> None:
    pending = (
        await client.post(
            f"{API}/modules/{drafted.modules[0]}/lesson",
            json={"markdown": submission_text(TITLE)},
        )
    ).json()
    assert (await wait_session(client, pending["verification_session_id"]))["status"] == "completed"
    lesson_id = pending["id"]
    path = f"{API}/lessons/{lesson_id}"
    before = (await client.get(path)).json()
    resources = [
        {
            "url": "https://exemple.org/lire",
            "title": "Lecture",
            "type": "article",
            "reason": "Relire.",
        }
    ]
    rejected, failed = await submit(
        claude,
        "lessons_update_lesson",
        {"lesson_id": lesson_id, "resources": resources},
    )
    assert failed and rejected["data"]["error"]["code"] == "lesson_draft_required", rejected
    assert (await client.get(path)).json() == before

    started, failed = await submit(
        claude,
        "lessons_update_lesson",
        {"lesson_id": lesson_id, "title": "Bases relues"},
    )
    assert not failed, started
    await assert_played(client, app, started["data"]["session_id"])
