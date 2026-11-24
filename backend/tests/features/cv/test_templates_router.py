"""API des gabarits de CV (D126) : capture du design lancée sur le CV rangé dans la mémoire, refus
lisibles (vision désactivée, capture en cours, PDF illisible ou trop long, autre fichier), écarts
de police sans le nom lu dans le PDF, images des pages en PNG, gabarit actif, archivage, statut
qui suit la session, rien du CV ni du nom du gabarit dans les journaux."""

import logging
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select, update

from app.agents.tools.cv_template_port import CvTemplateStore
from app.db.models.agents import AgentSession
from app.db.models.career import CvReview, CvTemplate
from app.db.models.memory import Document
from app.features.settings.service import SettingsService
from app.providers.llm.base import ModelChoice
from app.providers.pdf.base import CV_TOO_LONG_MESSAGE
from scripts.sample_cv import CV_FACTS, SampleCv, make_cv_pdf
from tests.features.cv.conftest import API
from tests.features.cv.templates_support import SECRET_NAME
from tests.features.lessons.conftest import RecordingLauncher
from tests.features.postings.conftest import add_posting

TEMPLATES = f"{API}/cv/templates"
PNG = b"\x89PNG\r\n\x1a\n"


async def post(client: httpx.AsyncClient, pdf: bytes | None = None, **data: Any) -> httpx.Response:
    files = {"file": ("CV_Camille_Exemple.pdf", pdf or make_cv_pdf(), "application/pdf")}
    return await client.post(TEMPLATES, files=files, data={"name": SECRET_NAME, **data})


async def end_sessions(app: FastAPI, status: str = "completed") -> None:
    async with app.state.session_factory() as db:
        await db.execute(update(AgentSession).values(status=status))
        await db.commit()


def store(app: FastAPI) -> CvTemplateStore:
    port: CvTemplateStore = app.state.career.cv_templates
    return port


@pytest.fixture
async def settings_without_vision(client: httpx.AsyncClient, app: FastAPI) -> None:
    async with app.state.session_factory() as db:
        service = SettingsService(db, app.state.local_user_id)
        current = await service.get()
        tiers = {**current.tiers, "vision": ModelChoice(provider="glm", model="glm-4.7-flash")}
        await service.replace(current.model_copy(update={"tiers": tiers}))
        await db.commit()


async def test_create_template_launches_design_capture(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    r = await post(client)
    assert r.status_code == 202, r.text
    body = r.json()
    [(graph, inputs)] = launcher_spy.started
    assert (graph, inputs) == ("cv_capture", {"mode": "design", "template_id": body["template_id"]})
    t = (await client.get(f"{TEMPLATES}/{body['template_id']}")).json()
    assert (t["status"], t["session_id"], t["name"], t["active"]) == (
        "capturing",
        body["session_id"],
        SECRET_NAME,
        False,
    )
    assert (t["page_count"], t["passes"], t["score"], t["selectable"]) == (1, 0, None, True)
    async with app.state.session_factory() as db:
        row = await db.get(CvTemplate, body["template_id"])
        assert row is not None and row.document_id  # le CV d'origine reste relisible (G26)
        document = await db.get(Document, row.document_id)
        assert document is not None and document.tags == ["cv"]
    listed = (await client.get(TEMPLATES)).json()
    assert [item["id"] for item in listed] == [body["template_id"]]


async def test_create_from_an_imported_cv(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    first = (await post(client)).json()
    await end_sessions(app, "failed")
    async with app.state.session_factory() as db:
        row = await db.get(CvTemplate, first["template_id"])
        assert row is not None
        document_id = row.document_id
    r = await client.post(TEMPLATES, data={"name": "Autre", "document_id": document_id})
    assert r.status_code == 202, r.text
    async with app.state.session_factory() as db:
        again = await db.get(CvTemplate, r.json()["template_id"])
        assert again is not None and again.document_id == document_id
    missing = await client.post(TEMPLATES, data={"name": "Autre", "document_id": "inconnu"})
    assert missing.status_code == 404


async def test_vision_disabled_is_409(
    client: httpx.AsyncClient, settings_without_vision: None, launcher_spy: RecordingLauncher
) -> None:
    r = await post(client)
    assert r.status_code == 409
    assert r.json()["error"] == {
        "code": "vision_unavailable",
        "message": "Template capture needs a model that can read images. Enable one in Settings.",
        "details": None,
    }
    assert launcher_spy.started == []


async def test_five_page_pdf_is_422(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    r = await post(client, make_cv_pdf(SampleCv(pages=5)))
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "pdf_unreadable"
    assert r.json()["error"]["message"] == CV_TOO_LONG_MESSAGE
    assert launcher_spy.started == []
    async with app.state.session_factory() as db:  # rien n'est rangé
        assert (await db.execute(select(CvTemplate))).first() is None
        assert (await db.execute(select(Document))).first() is None


async def test_refusals(client: httpx.AsyncClient, launcher_spy: RecordingLauncher) -> None:
    text = {"file": ("cv.txt", b"pas un PDF", "text/plain")}
    r = await client.post(TEMPLATES, files=text, data={"name": "CV"})
    assert (r.status_code, r.json()["error"]["code"]) == (415, "unsupported_file_type")
    r = await client.post(TEMPLATES, data={"name": "CV"})  # ni fichier ni document
    assert r.status_code == 422 and r.json()["error"]["details"]["fields"] == [
        "file",
        "document_id",
    ]
    r = await post(client, name="x" * 121)
    assert r.status_code == 422 and r.json()["error"]["details"] == {"fields": ["name"]}
    assert "x" * 121 not in r.text
    assert launcher_spy.started == []


async def test_one_capture_at_a_time(
    client: httpx.AsyncClient, launcher_spy: RecordingLauncher
) -> None:
    first = (await post(client)).json()
    r = await post(client)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "capture_in_progress"
    assert r.json()["error"]["details"] == {"session_id": first["session_id"]}


async def test_font_gap_is_reported(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    created = (await post(client, make_cv_pdf(SampleCv(font="Calibri")))).json()
    await store(app).prepare(app.state.local_user_id, created["template_id"])
    t = (await client.get(f"{TEMPLATES}/{created['template_id']}")).json()
    assert any("Carlito" in gap for gap in t["font_gaps"])
    assert not any("Calibri" in gap for gap in t["font_gaps"])
    assert t["fonts"] == [
        {"role": "body", "family": "Carlito", "substitute": True},
        {"role": "heading", "family": "Carlito", "substitute": True},
    ]
    assert "Calibri" not in (await client.get(TEMPLATES)).text


async def test_page_images_served_as_png(
    client: httpx.AsyncClient, launcher_spy: RecordingLauncher
) -> None:
    template_id = (await post(client)).json()["template_id"]
    r = await client.get(f"{TEMPLATES}/{template_id}/pages/original/1")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert r.content.startswith(PNG)
    for path in ("original/2", "original/0", "render/1", "autre/1"):
        missing = await client.get(f"{TEMPLATES}/{template_id}/pages/{path}")
        assert missing.status_code == 404, path
    assert (await client.get(f"{TEMPLATES}/inconnu/pages/original/1")).status_code == 404


async def test_activate_only_ready(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    user = app.state.local_user_id
    first = (await post(client)).json()["template_id"]
    r = await client.post(f"{TEMPLATES}/{first}/activate")
    assert (r.status_code, r.json()["error"]["code"]) == (409, "template_not_ready")
    await store(app).finish(user, first, "ready", None)
    await end_sessions(app)
    second = (await post(client)).json()["template_id"]
    await store(app).finish(user, second, "ready", None)
    assert (await client.post(f"{TEMPLATES}/{second}/activate")).status_code == 204
    listed = {item["id"]: item["active"] for item in (await client.get(TEMPLATES)).json()}
    assert listed == {first: False, second: True}


async def test_delete_archives_unless_a_review_uses_it(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    user = app.state.local_user_id
    used = (await post(client)).json()["template_id"]
    await store(app).finish(user, used, "ready", None)
    await end_sessions(app)
    posting_id = await add_posting(app.state.session_factory, user)
    async with app.state.session_factory() as db:
        db.add(CvReview(user_id=user, posting_id=posting_id, template_id=used, profile_version=1))
        await db.commit()
    r = await client.delete(f"{TEMPLATES}/{used}")
    assert (r.status_code, r.json()["error"]["code"]) == (409, "template_in_use")
    assert r.json()["error"]["message"] == (
        "Finish the review using this template before deleting it."
    )
    other = (await post(client)).json()["template_id"]
    r = await client.delete(f"{TEMPLATES}/{other}")  # sa capture tourne encore
    assert (r.status_code, r.json()["error"]["code"]) == (409, "capture_in_progress")
    await end_sessions(app, "cancelled")
    assert (await client.delete(f"{TEMPLATES}/{other}")).status_code == 204
    assert (await client.delete(f"{TEMPLATES}/{other}")).status_code == 204  # idempotent
    assert [item["id"] for item in (await client.get(TEMPLATES)).json()] == [used]
    assert (await client.get(f"{TEMPLATES}/{other}")).status_code == 404


async def test_template_follows_a_failed_session(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    template_id = (await post(client)).json()["template_id"]
    await end_sessions(app, "failed")  # panne du modèle, plafond, délai de nœud
    t = (await client.get(f"{TEMPLATES}/{template_id}")).json()
    assert t["status"] == "failed"
    assert t["failure_reason"] == "Template capture stopped early. Restart it to continue."
    assert (await post(client)).status_code == 202  # plus aucune capture en cours


async def test_template_names_never_logged(
    client: httpx.AsyncClient,
    app: FastAPI,
    launcher_spy: RecordingLauncher,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    caplog.set_level(logging.DEBUG, logger="app")
    created = (await post(client, make_cv_pdf(SampleCv(font="Calibri")))).json()
    user = app.state.local_user_id
    await store(app).prepare(user, created["template_id"])
    await client.get(f"{TEMPLATES}/{created['template_id']}")
    assert created["template_id"] in caplog.text
    for secret in (SECRET_NAME, "Calibri", "Carlito", "CV_Camille", CV_FACTS["name"]):
        assert secret not in caplog.text, secret
