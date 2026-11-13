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
from app.features.cv.service.ats_checks import EDGE_BAND, ats_checks
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


def _margins(top: float, side: float = 12) -> PageSpec:
    return PageSpec(width_pt=595, height_pt=842, margins_mm=(top, side, side, side))


async def test_thin_top_margin_is_kept_and_reaches_target(gotenberg: str) -> None:
    """Revue 6.4, round 2, R1 : un original à 5 mm de marge haute garde ses 5 mm (aucun plancher
    n'abaisse le contenu), et un rendu fidèle à 1 mm près atteint la cible."""
    cv = content()
    _, original = await _render(gotenberg, _template(page=_margins(5)), cv)
    first = min(block.top for block in original.pages[0].blocks)
    assert first < 8 * 72 / 25.4, first  # sous 8 mm : le contenu suit la marge du spec
    _, faithful = await _render(gotenberg, _template(page=_margins(6)), cv)
    sim = similarity(original.pages, faithful.pages)
    assert sim.score >= TARGET_SCORE, sim


async def test_contact_in_band_with_zero_margin_passes(gotenberg: str) -> None:
    """Revue 6.4, round 2, R1 : bandeau collé au haut de la page (marges à 0), coordonnées sous le
    nom dans la bande haute des 4 % : `contact_in_body` passe. Nom de 14 pt sans titre, pour que
    les coordonnées tombent vraiment dans la bande."""
    cv = content(headline=None)
    template = _template(page=_margins(0, side=0))
    template.fonts.name_pt = 14
    _, layout = await _render(gotenberg, template, cv)
    page = layout.pages[0]
    contact = [b for b in page.blocks if CV_FACTS["email"] in b.text or CV_FACTS["phone"] in b.text]
    assert contact and min(block.top for block in contact) < EDGE_BAND * page.height_pt
    checks = {check.id: check for check in ats_checks(layout, cv)}
    assert checks["contact_in_body"].passed, checks["contact_in_body"]
