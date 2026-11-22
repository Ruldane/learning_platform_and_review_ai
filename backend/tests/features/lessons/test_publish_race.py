"""La fin d'une publication supplantée ne restaure pas ses artefacts."""

import asyncio

import httpx
import pytest
from fastapi import FastAPI

from app.agents.tools.lesson_port import LessonReport
from app.features.lessons.service.store import AgentLessonStore
from app.providers.pdf.base import HtmlDocument
from tests.agents.graphs.lesson_support import LessonModels
from tests.features.lessons.test_router import seed
from tests.support.direct import API, Seed
from tests.support.lesson_verification import lesson_memory, submission_text, wait_session
from tests.support.memory import FakeHtmlRenderer

pytestmark = pytest.mark.usefixtures("settled_indexing")


async def test_delayed_old_renderer_cannot_restore_previous_pdf_or_memory(
    client: httpx.AsyncClient,
    app: FastAPI,
    drafted: Seed,
    accept_lesson: LessonModels,
    monkeypatch: pytest.MonkeyPatch,
    fake_html_renderer: FakeHtmlRenderer,
) -> None:
    entered, release = asyncio.Event(), asyncio.Event()

    async def render(document: HtmlDocument, *, timeout_s: float = 60) -> bytes:
        if "Ancienne explication" in document.index_html:
            entered.set()
            await release.wait()
            return b"%PDF-1.7 ancien"
        return b"%PDF-1.7 nouveau"

    monkeypatch.setattr(fake_html_renderer, "html_to_pdf", render)
    store = AgentLessonStore(app.state.lessons)
    old = submission_text("Module Bases", "Ancienne explication")
    new = submission_text("Module Bases", "Nouvelle explication")
    module_id = drafted.modules[0]
    published = asyncio.create_task(
        store.publish(
            drafted.user_id,
            "ancienne-session",
            module_id,
            markdown=old,
            resources=(),
            report=LessonReport(1500, (), (), 0),
        )
    )
    try:
        async with asyncio.timeout(20):
            await entered.wait()
        [lesson] = (await client.get(f"{API}/programs/{drafted.program_id}/lessons")).json()
        path = f"{API}/lessons/{lesson['id']}"
        pending = await client.patch(path, json={"markdown": new})
        assert pending.status_code == 202
        done = await wait_session(client, pending.json()["verification_session_id"])
        assert done["status"] == "completed", done
    finally:
        release.set()
        await published

    assert (await client.get(f"{path}/pdf")).content == b"%PDF-1.7 nouveau"
    assert [item.text for item in await lesson_memory(app)] == [new.strip()]


@pytest.mark.parametrize("recover", [False, True])
async def test_patch_with_a_pdf_keeps_publication_until_the_replacement_pdf_is_ready(
    client: httpx.AsyncClient,
    app: FastAPI,
    accept_lesson: LessonModels,
    monkeypatch: pytest.MonkeyPatch,
    fake_html_renderer: FakeHtmlRenderer,
    recover: bool,
) -> None:
    seeded = await seed(app)
    path = f"{API}/lessons/{seeded.lesson_id}"
    old = (await client.get(path)).json()
    old_pdf = (await client.get(f"{path}/pdf")).content
    new = submission_text(old["title"], "Nouvelle explication")
    entered, release = asyncio.Event(), asyncio.Event()
    attempts = 0

    async def render(document: HtmlDocument, *, timeout_s: float = 60) -> bytes:
        nonlocal attempts
        attempts += 1
        entered.set()
        await release.wait()
        if attempts == 1 or not recover:
            raise TimeoutError
        return b"%PDF-1.7 nouvelle version"

    monkeypatch.setattr(fake_html_renderer, "html_to_pdf", render)
    pending = await client.patch(path, json={"markdown": new})
    assert pending.status_code == 202
    try:
        async with asyncio.timeout(20):
            await entered.wait()
        assert (await client.get(path)).json()["markdown"] == old["markdown"]
        assert (await client.get(f"{path}/pdf")).content == old_pdf
    finally:
        release.set()

    sid = pending.json()["verification_session_id"]
    done = await wait_session(client, sid)
    current = (await client.get(path)).json()
    assert current["verification_session_id"] is None
    if recover:
        assert (done["status"], current["markdown"]) == ("completed", new)
        assert (await client.get(f"{path}/pdf")).content == b"%PDF-1.7 nouvelle version"
    else:
        assert (done["status"], current["markdown"]) == ("failed", old["markdown"])
        assert "PDF" in current["verification_failure_reason"]
        assert (await client.get(f"{path}/pdf")).content == old_pdf
        assert await lesson_memory(app) == []
    assert attempts == 2
    assert [item.agent for item in accept_lesson.calls].count("verifier") == 1
