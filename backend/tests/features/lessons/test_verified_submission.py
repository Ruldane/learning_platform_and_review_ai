"""Écritures de leçon avec la vraie Fabrique et des fournisseurs déterministes."""

import asyncio
import json

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select

from app.agents.tools.lesson_port import LessonReport
from app.core.errors import AppError
from app.db.models.agents import AgentSession
from app.db.models.lessons import Lesson
from app.features.lessons.service.store import AgentLessonStore
from tests.agents.graphs.lesson_support import LessonModels
from tests.features.lessons.test_router import seed
from tests.mcp.adapter_support import call
from tests.mcp.support import Mcp
from tests.support.direct import API, Seed
from tests.support.lesson_verification import lesson_memory, submission_text, wait_session
from tests.support.lessons import verifier_reply

TITLE = "Titre soumis"
DRAFT = submission_text(TITLE)

pytestmark = pytest.mark.usefixtures("settled_indexing")


async def test_post_keeps_the_draft_private_until_the_verifier_completes(
    client: httpx.AsyncClient, app: FastAPI, drafted: Seed, accept_lesson: LessonModels
) -> None:
    release = asyncio.Event()

    async def gate(agent: str, prompt: str) -> None:
        if agent == "verifier":
            await release.wait()

    accept_lesson.hooks.append(gate)
    response = await client.post(
        f"{API}/modules/{drafted.modules[0]}/lesson", json={"title": TITLE, "markdown": DRAFT}
    )

    assert response.status_code == 202, response.text
    pending = response.json()
    sid = pending["verification_session_id"]
    path = f"{API}/lessons/{pending['id']}"
    assert (pending["title"], pending["markdown"], pending["status"]) == (
        "Module Bases",
        "",
        "generating",
    )
    assert (await client.get(path)).json()["markdown"] == ""
    assert await lesson_memory(app) == []

    release.set()
    done = await wait_session(client, sid)

    assert done["status"] == "completed", done
    ready = (await client.get(path)).json()
    assert (ready["title"], ready["markdown"], ready["status"]) == (TITLE, DRAFT, "ready")
    assert ready["verification_session_id"] is None
    assert ready["pdf_available"] is True
    assert len(ready["resources"]) == 2
    assert [item.text for item in await lesson_memory(app)] == [DRAFT.strip()]
    assert [item.agent for item in accept_lesson.calls].count("writer") == 0


async def test_invalid_structure_is_rejected_before_agent_launch(
    client: httpx.AsyncClient, app: FastAPI, drafted: Seed
) -> None:
    invalid = DRAFT.replace("## Schémas", "## SECRET-DU-BROUILLON")
    response = await client.post(
        f"{API}/modules/{drafted.modules[0]}/lesson", json={"title": TITLE, "markdown": invalid}
    )

    assert response.status_code == 422, response.text
    error = response.json()["error"]
    assert error["code"] == "lesson_invalid"
    assert any("Section manquante" in item for item in error["details"]["reasons"])
    assert "SECRET-DU-BROUILLON" not in response.text
    assert await lesson_memory(app) == []
    async with app.state.session_factory() as db:
        assert list(await db.scalars(select(AgentSession.id))) == []


async def test_patch_keeps_the_published_text_and_pdf_until_it_is_verified(
    client: httpx.AsyncClient, app: FastAPI, accept_lesson: LessonModels
) -> None:
    seeded = await seed(app)
    path = f"{API}/lessons/{seeded.lesson_id}"
    previous = (await client.get(path)).json()
    pdf_before = (await client.get(f"{path}/pdf")).content
    release = asyncio.Event()

    async def gate(agent: str, prompt: str) -> None:
        if agent == "verifier":
            await release.wait()

    accept_lesson.hooks.append(gate)
    response = await client.patch(path, json={"title": TITLE, "markdown": DRAFT})

    assert response.status_code == 202, response.text
    pending = response.json()
    for field in ("title", "markdown", "pdf_available", "status"):
        assert pending[field] == previous[field]
    assert (await client.get(f"{path}/pdf")).content == pdf_before
    assert (await client.get(path)).json()["markdown"] == previous["markdown"]

    release.set()
    assert (await wait_session(client, pending["verification_session_id"]))["status"] == "completed"
    assert (await client.get(path)).json()["markdown"] == DRAFT


async def test_mcp_undo_revokes_permission_to_publish_a_pending_revision(
    client: httpx.AsyncClient, app: FastAPI, accept_lesson: LessonModels, claude: Mcp
) -> None:
    seeded = await seed(app)
    path = f"{API}/lessons/{seeded.lesson_id}"
    before = (await client.get(path)).json()
    release = asyncio.Event()
    entered = asyncio.Event()

    async def gate(agent: str, prompt: str) -> None:
        if agent == "verifier":
            entered.set()
            await release.wait()

    accept_lesson.hooks.append(gate)
    token = await claude.token(("lessons",), "write")
    result, error = await call(
        claude,
        token,
        "lessons_update_lesson",
        {"lesson_id": seeded.lesson_id, "title": TITLE, "markdown": DRAFT},
    )

    assert not error, result
    sid = result["data"]["verification_session_id"]
    async with asyncio.timeout(30):
        await entered.wait()
    [change] = (await claude.http.get(f"{API}/mcp/changes")).json()
    undone = await claude.http.post(f"{API}/mcp/changes/{change['call_id']}/undo")
    assert undone.status_code == 200, undone.text
    release.set()

    assert (await wait_session(client, sid))["status"] == "cancelled"
    assert (await client.get(path)).json() == before
    assert await lesson_memory(app) == []


def low_grade() -> str:
    response = json.loads(verifier_reply())
    response["grades"]["example"] = {"score": 60, "reason": "Un exemple trop bref."}
    return json.dumps(response)


async def test_the_verifier_requests_a_revision_of_the_submitted_text(
    client: httpx.AsyncClient, app: FastAPI, drafted: Seed, lesson_models: LessonModels
) -> None:
    revised = submission_text(TITLE, "Exemple révisé")
    lesson_models.when("verifier", "", low_grade(), verifier_reply())
    lesson_models.when("writer", "", revised)
    response = await client.post(
        f"{API}/modules/{drafted.modules[0]}/lesson", json={"title": TITLE, "markdown": DRAFT}
    )
    assert response.status_code == 202
    pending = response.json()

    assert (await wait_session(client, pending["verification_session_id"]))["status"] == "completed"

    lesson = (await client.get(f"{API}/lessons/{pending['id']}")).json()
    assert lesson["markdown"] == revised.strip()
    [writer] = [call for call in lesson_models.calls if call.agent == "writer"]
    assert "Un exemple trop bref." in writer.prompt and "notion0" in writer.prompt
    assert [item.text for item in await lesson_memory(app)] == [revised.strip()]
    async with app.state.session_factory() as db:
        record = await db.get(Lesson, pending["id"])
        assert record is not None and record.report is not None
        assert record.report["revisions"] == 1


async def test_refusal_keeps_the_published_version_and_exposes_a_reason(
    client: httpx.AsyncClient, app: FastAPI, lesson_models: LessonModels
) -> None:
    seeded = await seed(app)
    path = f"{API}/lessons/{seeded.lesson_id}"
    before = (await client.get(path)).json()
    lesson_models.when("verifier", "", low_grade(), low_grade(), low_grade())
    lesson_models.when("writer", "", DRAFT, DRAFT.replace("## Schémas", "## SECRET-DU-TEXTE"))

    response = await client.patch(path, json={"title": TITLE, "markdown": DRAFT})

    sid = response.json()["verification_session_id"]
    assert (await wait_session(client, sid))["status"] == "completed"
    denied = (await client.get(path)).json()
    assert denied["verification_session_id"] is None
    reason = denied.pop("verification_failure_reason")
    assert "2 révision(s)" in reason and "Exemple travaillé (60/100)" in reason
    # La dernière révision casse la structure : on revient à la meilleure version (D305).
    assert "Structure du chapitre" not in reason and "SECRET-DU-TEXTE" not in reason
    # Les remarques du Vérificateur sur la meilleure version, pour réviser à coup sûr (D308).
    feedback = denied.pop("verification_feedback")
    assert any("Un exemple trop bref." in item for item in feedback), feedback
    assert "SECRET-DU-TEXTE" not in json.dumps(feedback)
    before.pop("verification_failure_reason")
    assert before.pop("verification_feedback") == []
    assert denied == before
    assert await lesson_memory(app) == []

    # Une nouvelle soumission efface les remarques de la précédente.
    again = await client.patch(path, json={"title": TITLE, "markdown": DRAFT})
    assert again.status_code == 202, again.text
    assert again.json()["verification_feedback"] == []
    await wait_session(client, again.json()["verification_session_id"])


async def test_restart_recovers_the_draft_committed_with_its_session(
    client: httpx.AsyncClient,
    app: FastAPI,
    drafted: Seed,
    accept_lesson: LessonModels,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = app.state.runtime.runner
    with monkeypatch.context() as patch:
        patch.setattr(runner, "_launch", lambda *_: None)
        response = await client.post(
            f"{API}/modules/{drafted.modules[0]}/lesson",
            json={"title": TITLE, "markdown": DRAFT},
            headers={"X-Tremplin-Run": "openai"},
        )
    assert response.status_code == 202
    pending = response.json()
    sid = pending["verification_session_id"]
    async with app.state.session_factory() as db:
        row = await db.get(AgentSession, sid)
        assert row is not None and row.model_provider == "openai"
    assert await lesson_memory(app) == []

    assert await runner.recover_on_startup() == [sid]
    assert (await wait_session(client, sid))["status"] == "completed"
    assert (await client.get(f"{API}/lessons/{pending['id']}")).json()["markdown"] == DRAFT


async def test_replay_of_old_publication_cannot_publish_a_new_reservation(
    client: httpx.AsyncClient,
    app: FastAPI,
    drafted: Seed,
    accept_lesson: LessonModels,
) -> None:
    module_id = drafted.modules[0]
    made = await client.post(
        f"{API}/modules/{module_id}/lesson", json={"title": TITLE, "markdown": DRAFT}
    )
    old_sid = made.json()["verification_session_id"]
    assert (await wait_session(client, old_sid))["status"] == "completed"
    path = f"{API}/lessons/{made.json()['id']}"
    accept_lesson.block = lambda agent, _prompt: agent == "verifier"
    second = await client.patch(path, json={"title": "Nouveau titre"})
    assert second.status_code == 202, second.text
    assert second.json()["verification_session_id"] != old_sid

    # Simule le rejeu du nœud `publish` après un arrêt survenu entre le commit et le checkpoint.
    async with app.state.session_factory() as db:
        old_run = await db.get(AgentSession, old_sid)
        assert old_run is not None
        old_run.status = "running"
        await db.commit()
    store = AgentLessonStore(app.state.lessons)
    with pytest.raises(AppError) as refused:
        await store.publish(
            drafted.user_id,
            old_sid,
            module_id,
            markdown=DRAFT,
            resources=[],
            report=LessonReport(1500, (), (), 0),
            verification=True,
        )
    assert refused.value.code == "lesson_verification_revoked"
    still_pending = (await client.get(path)).json()
    assert still_pending["verification_session_id"] == second.json()["verification_session_id"]
    assert (still_pending["title"], still_pending["markdown"]) == (TITLE, DRAFT)
