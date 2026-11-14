"""Polices d'un gabarit (D126) : le texte prend la police la plus employée, les titres celle des
plus grandes tailles hors du nom ; un écart est toujours dit, sans le nom lu dans le PDF ; une
famille introuvable cède la place à Liberation Sans (ou Serif) de l'image de Gotenberg ; les
fichiers sont téléchargés une fois et réutilisés."""

from app.features.cv.service.fonts import (
    SCANNED_GAP,
    FontRole,
    Role,
    available_families,
    font_gaps,
    font_roles,
    font_uses,
    resolve_fonts,
)
from app.features.cv.service.runtime import CvRuntime
from app.providers.fonts.fake import FakeFontSource
from app.providers.pdf.base import PageLayout, PdfLayout, TextBlock
from scripts.sample_cv import SampleCv, make_cv_pdf


def block(text: str, font: str, size: float, *, invisible: bool = False) -> TextBlock:
    return TextBlock(text, 40, 40, 200, 40 + size, font, size, "#222222", False, invisible)


def layout(*pages: list[TextBlock]) -> PdfLayout:
    return PdfLayout(
        pages=[PageLayout(595, 842, list(blocks), b"", "") for blocks in pages],
        fonts=[],
        selectable=True,
    )


def roles_of(found: list[FontRole]) -> dict[str, tuple[str, str]]:
    return {role.role: (role.original, role.family) for role in found}


def test_body_is_most_used_and_heading_is_largest_outside_the_name() -> None:
    found = font_roles(
        layout(
            [
                block("Camille Exemple", "ABCDEF+Garamond-Bold", 24),  # le nom : écarté
                block("Expériences", "Cambria-Bold", 14),
                block("Une longue ligne de texte du corps du CV", "Calibri", 10),
                block("Encore du texte du corps", "Calibri", 10),
                block(
                    "Texte caché bien plus long que tout le reste du CV",
                    "Arial",
                    10,
                    invisible=True,
                ),
            ],
            [block("Formation", "Cambria", 14), block("Texte de la page deux", "Calibri", 10)],
        )
    )
    assert roles_of(found) == {"body": ("Calibri", "Carlito"), "heading": ("Cambria", "Caladea")}


def test_heading_falls_back_to_body_without_larger_text() -> None:
    found = font_roles(layout([block("Nom", "Lato", 20), block("Corps du texte", "Lato", 10)]))
    assert roles_of(found) == {"body": ("Lato", "Lato"), "heading": ("Lato", "Lato")}
    assert font_gaps(found, {"Lato"}) == []  # police libre : aucun écart
    assert all(not use.substitute for use in font_uses(found, {"Lato"}))


def test_gap_sentences_never_name_the_pdf_font() -> None:
    found = [
        FontRole("body", "Calibri", "Carlito", free=False, known=True),
        FontRole("heading", "Georgia", "Gelasio", free=False, known=True),
    ]
    assert font_gaps(found, {"Carlito", "Gelasio"}) == [
        "La police du texte n'est pas libre : remplacée par Carlito, très proche.",
        "La police des titres n'est pas libre : remplacée par Gelasio, proche.",
    ]
    roles: tuple[Role, ...] = ("body", "heading")
    unknown = [FontRole(r, "MaPoliceMaison", "Liberation Sans", False, False) for r in roles]
    assert font_gaps(unknown, set()) == [
        "La police du texte et des titres n'a pas d'équivalent connu : "
        "remplacée par Liberation Sans."
    ]


def test_unloaded_family_falls_back_to_the_gotenberg_image() -> None:
    found = [
        FontRole("body", "Lato", "Lato", free=True, known=False),
        FontRole("heading", "Cambria", "Caladea", free=False, known=True),
    ]
    gaps = font_gaps(found, set())
    assert gaps == [
        "La police du texte n'a pas pu être chargée : remplacée par Liberation Sans.",
        "La police des titres n'a pas pu être chargée : remplacée par Liberation Serif.",
    ]
    uses = {use.role: (use.family, use.substitute) for use in font_uses(found, set())}
    assert uses == {"body": ("Liberation Sans", True), "heading": ("Liberation Serif", True)}


def test_scanned_cv_has_no_font_and_says_so() -> None:
    assert font_roles(layout([])) == []
    assert font_gaps([], set()) == [SCANNED_GAP]
    assert {use.family for use in font_uses([], set())} == {"Liberation Sans"}


async def test_resolve_fonts_downloads_the_free_family(cv_runtime: CvRuntime) -> None:
    fonts = cv_runtime.fonts
    assert isinstance(fonts, FakeFontSource)
    pdf = await cv_runtime.layout.extract_layout(make_cv_pdf(SampleCv(font="Calibri")))
    files, uses, gaps = await resolve_fonts(cv_runtime, "u1", pdf)
    assert {(f.family, f.weight) for f in files} == {("Carlito", 400), ("Carlito", 700)}
    assert {use.family for use in uses} == {"Carlito"} and all(use.substitute for use in uses)
    assert any("Carlito" in gap for gap in gaps) and not any("Calibri" in gap for gap in gaps)
    assert fonts.calls == [("Carlito", (400, 700))]


async def test_unavailable_family_attaches_no_file(cv_runtime: CvRuntime) -> None:
    fonts = cv_runtime.fonts
    assert isinstance(fonts, FakeFontSource)
    fonts.unavailable.add("Carlito")
    pdf = await cv_runtime.layout.extract_layout(make_cv_pdf(SampleCv(font="Calibri")))
    files, uses, gaps = await resolve_fonts(cv_runtime, "u1", pdf)
    assert files == [] and {use.family for use in uses} == {"Liberation Sans"}
    assert gaps == [
        "La police du texte et des titres n'a pas pu être chargée : remplacée par Liberation Sans."
    ]


def test_available_families_always_offer_the_image_fonts() -> None:
    assert available_families([]) == ["Liberation Sans", "Liberation Serif"]
