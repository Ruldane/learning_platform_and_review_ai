"""Export PDF du programme (SPEC 3.4, D89) : gabarit sans script, rendu à la demande, isolé par
utilisateur, 502 lisible si Gotenberg échoue. Faux rendu : aucun Gotenberg."""

import logging
import re

import httpx
import pytest
from fastapi import FastAPI

from app.features.program.schemas import ProgramOut
from app.features.program.service.export_pdf import program_document
from tests.features.program.conftest import Draft
from tests.features.program.support import API, view
from tests.sessions_support import act_as
from tests.support.memory import FakeHtmlRenderer


async def test_program_pdf_route_returns_pdf(
    client: httpx.AsyncClient, draft_program: Draft, fake_html_renderer: FakeHtmlRenderer
) -> None:
    r = await client.get(f"{API}/programs/{draft_program.program_id}/export.pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert 'filename="programme.pdf"' in r.headers["content-disposition"]
    assert r.content.startswith(b"%PDF")
    [doc] = fake_html_renderer.documents
    assert "<script" not in doc.index_html and doc.wait_for_expression is None
    assert set(doc.assets) == {"program.css"}
    assert doc.footer_html is not None and "pageNumber" in doc.footer_html
    html = doc.index_html
    assert "<title>Parcours données</title>" in html
    assert "Lire le chapitre 1" in html and "Semaine 1 · Bases" in html
    assert html.count('<td class="day">') == 12  # une ligne par tâche


async def test_program_pdf_escapes_every_text(
    client: httpx.AsyncClient, draft_program: Draft
) -> None:
    program = ProgramOut.model_validate(await view(client, draft_program.program_id))
    trap = '<script>alert(1)</script><img src=x onerror="y()">'
    weeks = program.weeks
    weeks[0].theme = trap
    weeks[0].modules[0].title = trap
    weeks[0].modules[0].skills = [trap]
    weeks[0].modules[0].tasks[0].title = trap
    weeks[0].modules[0].tasks[0].done_criterion = trap
    html = program_document(program.model_copy(update={"title": trap})).index_html
    assert re.findall(r"<(script|img)", html) == []
    assert "&lt;script&gt;" in html and "onerror=&#34;" in html


async def test_program_pdf_isolated_between_users(
    client: httpx.AsyncClient,
    app: FastAPI,
    draft_program: Draft,
    fake_html_renderer: FakeHtmlRenderer,
) -> None:
    act_as(app, "quelqu-un-d-autre")
    try:
        r = await client.get(f"{API}/programs/{draft_program.program_id}/export.pdf")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 404 and r.json()["error"]["code"] == "program_not_found"
    assert fake_html_renderer.documents == []


async def test_program_pdf_render_failure_is_a_readable_502(
    client: httpx.AsyncClient,
    draft_program: Draft,
    fake_html_renderer: FakeHtmlRenderer,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    fake_html_renderer.failures = 1
    r = await client.get(f"{API}/programs/{draft_program.program_id}/export.pdf")
    assert r.status_code == 502
    error = r.json()["error"]
    assert error["code"] == "render_failed" and "réessaie" in error["message"]
    assert "Parcours données" not in r.text and "Parcours données" not in caplog.text
