"""CV rendu par un vrai Gotenberg puis relu par l'extracteur réel (6.4, D120) : marqué `live`,
désélectionné par défaut.

Gotenberg n'a aucun port publié : lancer un Gotenberg jetable avec les options de
`docker-compose.yml` et passer son adresse dans `GOTENBERG_URL` ; `CV_PDF_OUT` garde le PDF
pour le regarder."""

import os
from pathlib import Path

import httpx
import pytest

from app.agents.tools.cv_schema import CvContent
from app.agents.tools.template_schema import ColumnSpec, PageSpec, TemplateSpec
from app.agents.tools.template_similarity import TARGET_SCORE, similarity
from app.features.cv.service.ats_checks import ats_checks
from app.features.cv.service.template import cv_document
from app.providers.pdf.base import HTML_RENDER_TIMEOUT_S, PdfLayout
from app.providers.pdf.html import GotenbergHtmlRenderer
from app.providers.pdf.layout import LocalPdfLayoutExtractor
from scripts.sample_cv import CV_FACTS
from tests.support.cv_template import content, spec

pytestmark = pytest.mark.live


@pytest.fixture
def gotenberg() -> str:
    url = os.environ.get("GOTENBERG_URL")
    if not url:
        pytest.skip("GOTENBERG_URL n'est pas définie")
    return url


def _template(**changes: object) -> TemplateSpec:
    """Bandeau, colonne de gauche sombre **sans** couleur de texte, police de l'image."""
    columns = [
        ColumnSpec(width_pct=32, background="#2b2b2b", sections=["skills", "languages"]),
        ColumnSpec(width_pct=68, sections=["identity", "summary", "experience", "education"]),
    ]
    template = spec(columns=columns, header_band="#21549a", **changes)
    template.fonts.body = template.fonts.heading = "Liberation Sans"
    return template


async def _render(gotenberg: str, template: TemplateSpec, cv: CvContent) -> tuple[bytes, PdfLayout]:
    async with httpx.AsyncClient(trust_env=False, timeout=HTML_RENDER_TIMEOUT_S) as http:
        renderer = GotenbergHtmlRenderer(http, gotenberg)
        pdf = await renderer.html_to_pdf(cv_document(template, cv, []))
    return pdf, await LocalPdfLayoutExtractor().extract_layout(pdf)


async def test_rendered_template_extracts_back(gotenberg: str) -> None:
    """Rendu réel → texte sélectionnable (texte clair sur la colonne sombre), une page A4, les
    cinq contrôles au vert."""
    cv = content()
    pdf, layout = await _render(gotenberg, _template(), cv)
    assert pdf.startswith(b"%PDF")
    keep = os.environ.get("CV_PDF_OUT")
    if keep:
        Path(keep).write_bytes(pdf)
    assert len(layout.pages) == 1 and layout.selectable
    page = layout.pages[0]
    assert abs(page.width_pt - 595) < 1 and abs(page.height_pt - 842) < 1
    checks = ats_checks(layout, cv)
    assert all(check.passed for check in checks), checks
    assert CV_FACTS["email"] in " ".join(block.text for block in page.blocks)


async def test_small_margin_change_still_reaches_target(gotenberg: str) -> None:
    """Calibration sur un vrai couple : le même CV rendu avec 1 mm de marge en plus (≈ 3 pt de
    décalage) reste au-dessus de la cible ; une autre colonne de gauche la manque."""
    cv = content()
    _, original = await _render(gotenberg, _template(), cv)
    page = PageSpec(width_pt=595, height_pt=842, margins_mm=(13, 13, 12, 12))
    _, shifted = await _render(gotenberg, _template(page=page), cv)
    sim = similarity(original.pages, shifted.pages)
    assert sim.score >= TARGET_SCORE, sim
    other = spec()
    other.fonts.body = other.fonts.heading = "Liberation Sans"
    _, different = await _render(gotenberg, other, cv)
    assert similarity(original.pages, different.pages).score < TARGET_SCORE
