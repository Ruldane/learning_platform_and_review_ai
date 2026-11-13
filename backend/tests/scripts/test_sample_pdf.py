"""PDF minimal de test (`scripts.sample_pdf`) : taille de page et pagination (preflight G14)."""

import io

import pdfplumber

from scripts.sample_pdf import make_pdf


def _pages(pdf: bytes) -> list[tuple[float, float, str]]:
    with pdfplumber.open(io.BytesIO(pdf)) as document:
        return [(p.width, p.height, p.extract_text() or "") for p in document.pages]


def test_default_is_one_letter_page() -> None:
    assert _pages(make_pdf(["Bonjour Tremplin"])) == [(612, 792, "Bonjour Tremplin")]


def test_size_and_pages_split_lines_in_order() -> None:
    pages = _pages(make_pdf(["un", "deux", "trois"], size=(595, 842), pages=2))
    assert [(w, h) for w, h, _ in pages] == [(595, 842), (595, 842)]
    assert [text.split() for _, _, text in pages] == [["un", "deux"], ["trois"]]


def test_extra_pages_stay_blank() -> None:
    pages = _pages(make_pdf(["seule"], pages=3))
    assert [text for _, _, text in pages] == ["seule", "", ""]
