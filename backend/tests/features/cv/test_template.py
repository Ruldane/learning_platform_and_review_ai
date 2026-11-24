"""Gabarit HTML/CSS du CV écrit par le code à partir du spec (6.4, D120)."""

import re
from html import escape

import pytest

from app.agents.tools.template_schema import ColumnSpec
from app.features.cv.service.ats_checks import ats_checks
from app.features.cv.service.template import CV_CSP, cv_css, cv_document
from app.features.cv.service.templates_data import profile_content
from app.providers.fonts.base import FontFile
from app.providers.pdf.layout import LocalPdfLayoutExtractor
from scripts.sample_cv import CV_FACTS
from tests.support.cv_template import content, letter, spec
from tests.support.profile import profile
from tests.support.text_renderer import TextHtmlRenderer, visible_lines


def _body(html: str) -> str:
    return html.split("<body", 1)[1]


def test_cv_document_has_no_script_and_escapes_content() -> None:
    doc = cv_document(spec(), content(lines=["<script>alert(1)</script> & co"]), [])
    assert '<html lang="en">' in doc.index_html
    assert "<script>" not in doc.index_html and "&lt;script&gt;" in doc.index_html
    assert "&amp; co" in doc.index_html
    assert f'content="{escape(CV_CSP)}"' in doc.index_html.replace("&#39;", "&#x27;")
    assert "<img" not in doc.index_html and "javascript:" not in doc.index_html
    assert not any(name.endswith(".js") for name in doc.assets)


def test_profile_preview_uses_english_headings_and_preserves_profile_text() -> None:
    saved = profile()
    preview = profile_content(saved)
    assert [section.title for section in preview.sections] == [
        "Profile",
        "Experience",
        "Education",
        "Skills",
        "Languages",
    ]
    assert saved.summary is not None
    assert preview.sections[0].items[0].text == saved.summary.text
    assert preview.sections[-1].items[0].text == "Anglais C1"


def test_dom_order_is_column_one_then_two() -> None:
    html = cv_document(spec(), content(), []).index_html
    order = ["Camille Exemple", "Compétences", "Langues", "Profil", "Expérience professionnelle"]
    positions = [html.index(f">{text}<") for text in order]
    assert positions == sorted(positions)
    assert html.index('class="col col-1"') < html.index(">Compétences<")
    assert html.index('class="col col-2"') < html.index(">Profil<")
    assert re.findall(r"<h2>([^<]+)</h2>", html) == [
        "Compétences",
        "Langues",
        "Profil",
        "Expérience professionnelle",
        "Formation",
    ]


def test_section_missing_from_spec_goes_to_widest_column() -> None:
    columns = [
        ColumnSpec(width_pct=30, sections=["identity", "skills"]),
        ColumnSpec(width_pct=70, sections=["experience"]),
    ]
    html = cv_document(spec(columns=columns), content(), []).index_html
    for title in ("Profil", "Formation", "Langues"):
        assert html.index('class="col col-2"') < html.index(f"<h2>{title}</h2>")


def test_contact_is_in_body_not_header() -> None:
    doc = cv_document(spec(), content(), [])
    assert doc.footer_html is None
    body = _body(doc.index_html)
    assert CV_FACTS["email"] in body and CV_FACTS["phone"] in body
    assert CV_FACTS["email"] not in doc.index_html.split("<body", 1)[0]


def test_header_band_holds_identity_before_columns() -> None:
    html = cv_document(spec(header_band="#21549a"), content(), []).index_html
    band, columns = html.index('class="band"'), html.index('class="cols"')
    assert band < html.index(">Camille Exemple<") < html.index(CV_FACTS["email"]) < columns
    assert html.count(">Camille Exemple<") == 1 and "has-band" in html


def test_page_setup_follows_original() -> None:
    doc = cv_document(spec(page=letter()), content(), [])
    assert doc.page is not None
    assert (doc.page.width_in, doc.page.height_in) == ("8.5", "11")
    assert doc.page.margins_in == ("0", "0", "0", "0")
    a4 = cv_document(spec(), content(), []).page
    assert a4 is not None and (a4.width_in, a4.height_in) == ("8.2639", "11.6944")
    assert "@page { size: 612pt 792pt; margin: 0; }" in cv_css(spec(page=letter()), [])


@pytest.mark.parametrize(
    "changes",
    [
        {"accent": "red;}body{x:url(x)"},
        {"text": "#12345"},
        {"muted": "rgb(0,0,0)"},
        {"header_band": "#zzzzzz"},
    ],
)
def test_css_values_are_typed(changes: dict[str, str]) -> None:
    with pytest.raises(ValueError, match="#rrggbb"):
        cv_css(spec(**changes), [])


def test_css_refuses_font_outside_catalog_and_unbounded_numbers() -> None:
    bad_font = spec()
    bad_font.fonts.body = "Evil'; } * { background: url(x)"
    with pytest.raises(ValueError, match="catalogue"):
        cv_css(bad_font, [])
    bad_number = spec().model_copy(update={"gap_mm": float("nan")})
    with pytest.raises(ValueError, match="bornes"):
        cv_css(bad_number, [])
    css = cv_css(spec(), [])
    assert "url(" not in css and "--accent: #21549a;" in css
    assert "--grid: 32% 68%;" in css and "--body-pt: 10pt;" in css


def test_column_background_and_text_color_reach_css() -> None:
    columns = [
        ColumnSpec(width_pct=35, background="#1F4E79", text_color="#FFFFFF", sections=["identity"]),
        ColumnSpec(width_pct=65, sections=["experience"]),
    ]
    css = cv_css(spec(columns=columns), [])
    assert ".col-1 { background: #1f4e79; color: #ffffff; }" in css
    assert ".col-2 { background: transparent; color: var(--text); }" in css


def test_font_faces_point_to_attached_assets() -> None:
    fonts = [
        FontFile("Lato", 400, "normal", b"\x00\x01\x00\x00lato", ".ttf"),
        FontFile("Source Sans 3", 700, "normal", b"wOF2sans", ".woff2"),
    ]
    doc = cv_document(spec(), content(), fonts)
    css = doc.assets["cv.css"].decode()
    assert "src: url('lato-400.ttf') format('truetype'); font-weight: 400;" in css
    assert "src: url('source-sans-3-700.woff2') format('woff2'); font-weight: 700;" in css
    assert doc.assets["lato-400.ttf"] == fonts[0].data
    assert doc.assets["source-sans-3-700.woff2"] == fonts[1].data
    assert "--body-font: 'Lato', 'Liberation Sans', sans-serif;" in css
    assert {"base.css", "cv.css"} <= set(doc.assets)
    assert '<link rel="stylesheet" href="cv.css">' in doc.index_html
    with pytest.raises(ValueError, match="catalogue"):
        cv_css(spec(), [FontFile("Comic Sans", 400, "normal", b"x", ".ttf")])


def test_sections_use_h2_and_fact_text_only() -> None:
    html = cv_document(spec(), content(), []).index_html
    assert html.count("<h2>") == 5 and "x1a1" not in html  # ids de faits jamais rendus


async def test_dom_order_and_headings_pass_reading_checks_on_text_render() -> None:
    """Rendu textuel (ordre du DOM) puis extraction réelle : l'ordre de lecture et les intitulés
    du gabarit passent. Tailles et place du contact viennent du faux rendu (12 pt, 72 pt du haut) :
    elles ne se vérifient qu'en `live` (`test_template_live.py`)."""
    renderer = TextHtmlRenderer()
    cv = content()
    pdf = await renderer.html_to_pdf(cv_document(spec(), cv, []))
    layout = await LocalPdfLayoutExtractor().extract_layout(pdf)
    assert len(layout.pages) == 1 and (layout.pages[0].width_pt, layout.pages[0].height_pt) == (
        595,
        842,
    )
    checks = ats_checks(layout, cv)
    assert [check.id for check in checks] == [
        "selectable_text",
        "reading_order",
        "standard_headings",
        "contact_in_body",
        "font_sizes",
    ]
    assert all(check.passed for check in checks), checks


async def test_text_renderer_pages_are_adjustable() -> None:
    renderer = TextHtmlRenderer(pages=(2, 1))
    document = cv_document(spec(page=letter()), content(), [])
    extractor = LocalPdfLayoutExtractor()
    first = await extractor.extract_layout(await renderer.html_to_pdf(document))
    second = await extractor.extract_layout(await renderer.html_to_pdf(document))
    assert [len(first.pages), len(second.pages)] == [2, 1]
    assert (first.pages[0].width_pt, first.pages[0].height_pt) == (612, 792)
    assert len(renderer.documents) == 2
    assert "Camille Exemple" in visible_lines(document.index_html)
    assert "CV" not in visible_lines(document.index_html)  # <title> n'est pas visible


def test_dark_column_without_text_color_gets_light_text() -> None:
    columns = [
        ColumnSpec(width_pct=32, background="#2b2b2b", sections=["identity", "skills"]),
        ColumnSpec(width_pct=68, sections=["experience"]),
    ]
    css = cv_css(spec(columns=columns), [])
    assert ".col-1 { background: #2b2b2b; color: #ffffff; --muted: #d9d9d9; }" in css
    assert "body:not(.titles-band) .col-1 h2 { color: #ffffff; }" in css
    assert ".col-2 { background: transparent; color: var(--text); }" in css


def test_sections_sharing_a_key_are_all_rendered() -> None:
    cv = content()
    cv.sections.append(cv.sections[3].model_copy(update={"title": "Outils"}))
    html = cv_document(spec(), cv, []).index_html
    assert "<h2>Compétences</h2>" in html and "<h2>Outils</h2>" in html


def test_serif_families_fall_back_to_a_serif() -> None:
    template = spec()
    template.fonts.heading = "Lora"
    css = cv_css(template, [])
    assert "--heading-font: 'Lora', 'Liberation Serif', serif;" in css
