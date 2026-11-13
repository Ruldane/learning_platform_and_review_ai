"""CV rendu par un vrai Gotenberg puis relu par l'extracteur réel (6.4, D120) : marqué `live`,
désélectionné par défaut.

Gotenberg n'a aucun port publié : lancer un Gotenberg jetable avec les options de
`docker-compose.yml` et passer son adresse dans `GOTENBERG_URL` ; `CV_PDF_OUT` garde le PDF
pour le regarder."""

import os
from pathlib import Path

import httpx
import pytest

from app.agents.tools.template_similarity import similarity
from app.features.cv.service.ats_checks import ats_checks
from app.features.cv.service.template import cv_document
from app.providers.pdf.base import HTML_RENDER_TIMEOUT_S
from app.providers.pdf.html import GotenbergHtmlRenderer
from app.providers.pdf.layout import LocalPdfLayoutExtractor
from scripts.sample_cv import CV_FACTS, make_cv_pdf
from tests.support.cv_template import content, spec

pytestmark = pytest.mark.live


@pytest.fixture
def gotenberg() -> str:
    url = os.environ.get("GOTENBERG_URL")
    if not url:
        pytest.skip("GOTENBERG_URL n'est pas définie")
    return url


async def test_rendered_template_extracts_back(gotenberg: str) -> None:
    """Rendu réel → texte sélectionnable, une page A4, les cinq contrôles au vert."""
    template = spec(header_band="#21549a")
    template.fonts.body = template.fonts.heading = "Liberation Sans"  # police de l'image
    cv = content()
    async with httpx.AsyncClient(trust_env=False, timeout=HTML_RENDER_TIMEOUT_S) as http:
        pdf = await GotenbergHtmlRenderer(http, gotenberg).html_to_pdf(
            cv_document(template, cv, [])
        )
    assert pdf.startswith(b"%PDF")
    keep = os.environ.get("CV_PDF_OUT")
    if keep:
        Path(keep).write_bytes(pdf)
    extractor = LocalPdfLayoutExtractor()
    layout = await extractor.extract_layout(pdf)
    assert len(layout.pages) == 1 and layout.selectable
    page = layout.pages[0]
    assert abs(page.width_pt - 595) < 1 and abs(page.height_pt - 842) < 1
    checks = ats_checks(layout, cv)
    assert all(check.passed for check in checks), checks
    assert CV_FACTS["email"] in " ".join(block.text for block in page.blocks)
    # Le rendu ressemble au CV fictif d'origine (bandeau, deux colonnes) sans lui être identique.
    original = await extractor.extract_layout(make_cv_pdf())
    sim = similarity(original.pages, layout.pages)
    assert 30 < sim.score < 100 and sim.pages_render == 1
