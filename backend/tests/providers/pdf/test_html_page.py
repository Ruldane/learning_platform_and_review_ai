"""Taille de page, marges et polices jointes du rendu HTML (D119)."""

import pytest

from app.providers.pdf.base import HtmlDocument, PageSetup
from app.providers.pdf.html import html_form


def _fields(form: list[tuple[str, tuple[object, ...]]]) -> dict[str, object]:
    return {name: value[1] for name, value in form if name != "files"}


def test_html_form_with_page_setup_and_fonts() -> None:
    form = html_form(
        HtmlDocument("…", {"cv.css": b"", "lato-400.woff2": b"x"}, page=PageSetup("8.5", "11"))
    )
    assert ("paperWidth", (None, "8.5")) in form and ("marginTop", (None, "0")) in form
    assert any(
        f[1][0] == "lato-400.woff2" and f[1][2] == "font/woff2" for f in form if f[0] == "files"
    )
    assert _fields(form) == {
        "paperWidth": "8.5",
        "paperHeight": "11",
        "marginTop": "0",
        "marginBottom": "0",
        "marginLeft": "0",
        "marginRight": "0",
        "printBackground": "true",
    }


def test_truetype_font_and_margin_order() -> None:
    page = PageSetup("8.27", "11.7", ("0.1", "0.2", "0.3", "0.4"))
    form = html_form(HtmlDocument("…", {"source-sans-3-700.ttf": b"x"}, page=page))
    fields = _fields(form)
    assert (fields["marginTop"], fields["marginRight"]) == ("0.1", "0.2")
    assert (fields["marginBottom"], fields["marginLeft"]) == ("0.3", "0.4")
    assert any(f[1][2] == "font/ttf" for f in form if f[0] == "files")


def test_no_page_keeps_a4_with_lesson_margins() -> None:
    fields = _fields(html_form(HtmlDocument("…", {})))
    assert (fields["paperWidth"], fields["paperHeight"]) == ("8.27", "11.7")
    assert {fields[f"margin{side}"] for side in ("Top", "Bottom", "Left", "Right")} == {"0.6"}


@pytest.mark.parametrize(
    "name", ["Lato-400.ttf", "lato.otf", "index.html", "../lato.ttf", "a.woff"]
)
def test_font_names_must_be_slugs(name: str) -> None:
    with pytest.raises(ValueError):
        HtmlDocument("…", {name: b"x"})


@pytest.mark.parametrize(
    "setup", [("8.5in", "11"), ("8,5", "11"), ("", "11"), ("8.5", "11; x=1"), ("123", "11")]
)
def test_page_setup_refuses_other_than_inches(setup: tuple[str, str]) -> None:
    with pytest.raises(ValueError):
        PageSetup(*setup)
