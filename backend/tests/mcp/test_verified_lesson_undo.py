"""L'annulation MCP d'une leçon vérifiée restaure sa publication et ses ressources."""

import httpx
import pytest
from fastapi import FastAPI

from app.db.models.memory import MemoryItem
from tests.mcp.adapter_support import call
from tests.mcp.support import API, Mcp
from tests.mcp.test_direct_write import count, undo_last, writer
from tests.support.direct import Seed
from tests.support.lesson_verification import lesson_memory, submission_text, wait_session
from tests.support.memory import FakeHtmlRenderer

pytestmark = pytest.mark.usefixtures("settled_indexing")
READING = {
    "url": "https://exemple.org/fiche",
    "title": "Fiche ajoutée",
    "type": "article",
    "reason": "Relire le chapitre.",
}


@pytest.mark.usefixtures("accept_lesson")
async def test_a_published_submission_and_its_resources_can_be_undone(
    client: httpx.AsyncClient,
    app: FastAPI,
    drafted: Seed,
    claude: Mcp,
) -> None:
    token = await writer(claude)
    made, _ = await call(
        claude,
        token,
        "lessons_write_lesson",
        {
            "module_id": drafted.modules[0],
            "markdown": submission_text("Module Bases"),
            "resources": [READING],
        },
    )
    lesson_id = made["data"]["id"]

    assert (await wait_session(client, made["data"]["verification_session_id"]))[
        "status"
    ] == "completed"
    ready = (await client.get(f"{API}/lessons/{lesson_id}")).json()
    assert ready["status"] == "ready" and ready["markdown"] == submission_text("Module Bases")
    assert READING["url"] in {row["url"] for row in ready["resources"]}
    [item] = await lesson_memory(app)
    assert item.text == ready["markdown"].strip() and item.created_by == "claude"

    undone = await undo_last(claude)
    assert undone.status_code == 200, undone.text
    assert (await client.get(f"{API}/lessons/{lesson_id}")).status_code == 404
    assert (
        await client.get(f"{API}/resources", params={"program_id": drafted.program_id})
    ).json() == []
    assert await count(app, MemoryItem, kind="lesson") == 0


@pytest.mark.usefixtures("accept_lesson")
async def test_undo_published_revision_restores_the_previous_text_pdf_and_resources(
    client: httpx.AsyncClient,
    app: FastAPI,
    drafted: Seed,
    claude: Mcp,
    fake_html_renderer: FakeHtmlRenderer,
) -> None:
    token = await writer(claude)
    old = submission_text("Module Bases", "La version d’origine.")
    fake_html_renderer.pdf = b"%PDF-1.7 ancien"
    made, error = await call(
        claude,
        token,
        "lessons_write_lesson",
        {"module_id": drafted.modules[0], "markdown": old},
    )
    assert not error
    info = made["data"]
    assert (await wait_session(client, info["verification_session_id"]))["status"] == "completed"
    path = f"{API}/lessons/{info['id']}"
    before = (await client.get(path)).json()
    assert (await client.get(f"{path}/pdf")).content == b"%PDF-1.7 ancien"

    new = submission_text("Module Bases", "La version suivante.")
    fake_html_renderer.pdf = b"%PDF-1.7 revision"
    updated, error = await call(
        claude,
        token,
        "lessons_update_lesson",
        {"lesson_id": info["id"], "markdown": new, "resources": [READING]},
    )
    assert not error
    sid = updated["data"]["verification_session_id"]
    assert (await wait_session(client, sid))["status"] == "completed"
    assert (await client.get(f"{path}/pdf")).content == fake_html_renderer.pdf

    undone = await undo_last(claude)

    assert undone.status_code == 200, undone.text
    assert (await client.get(path)).json() == before
    assert (await client.get(f"{path}/pdf")).content == b"%PDF-1.7 ancien"
    assert [item.text for item in await lesson_memory(app)] == [old.strip()]
