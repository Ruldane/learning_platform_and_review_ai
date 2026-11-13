"""Score de ressemblance entre l'original et le rendu d'un gabarit (6.4, D120), sur des pages
fictives dessinées par le test (72 dpi : 1 pixel = 1 point) et sur du texte réel relu par
l'extracteur (`make_pdf`, calibration du score)."""

import io

import pytest
from PIL import Image, ImageDraw

from app.agents.tools.template_grids import SHIFT_MIN_PT
from app.agents.tools.template_similarity import (
    MAX_FIX_PASSES,
    TARGET_SCORE,
    W_COLOR,
    W_INK,
    W_TEXT,
    Similarity,
    ZoneDiff,
    describe,
    similarity,
)
from app.providers.pdf.base import PageLayout, TextBlock
from app.providers.pdf.layout import LocalPdfLayoutExtractor
from scripts.sample_pdf import make_pdf

WIDTH, HEIGHT = 595, 842
BLUE = (33, 84, 154)
RED = (190, 30, 30)
INK = (34, 34, 34)
# 50 lignes de longueurs variées, comme un CV (des lignes toutes égales seraient indiscernables
# d'une ligne à l'autre).
_SENTENCE = "Conception d un assistant interne avec LangGraph pour le support client et la gestion"
_WORDS = [*_SENTENCE.split(), "des", "demandes"]
LINES = [" ".join(_WORDS[: 2 + (index * 7) % 15]) for index in range(50)]


def _png(image: Image.Image) -> bytes:
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def _block(x0: float, top: float, x1: float, bottom: float) -> TextBlock:
    return TextBlock("ligne", x0, top, x1, bottom, "Lato", 10, "#222222", False, False)


def cv_page(left: float = 0.30, accent: tuple[int, int, int] = BLUE) -> PageLayout:
    """Colonne de gauche pleine (couleur d'accent) sur `left` de la largeur, lignes de texte
    sombres à droite."""
    image = Image.new("RGB", (WIDTH, HEIGHT), "white")
    draw = ImageDraw.Draw(image)
    column = round(WIDTH * left)
    draw.rectangle((0, 0, column - 1, HEIGHT - 1), fill=accent)
    blocks = []
    for row in range(30):
        top = 60 + 24 * row
        x0, x1 = column + 20, WIDTH - 40
        draw.rectangle((x0, top, x1, top + 9), fill=INK)
        blocks.append(_block(x0, top, x1, top + 10))
    return PageLayout(WIDTH, HEIGHT, blocks, _png(image), "texte")


def blank_page() -> PageLayout:
    return PageLayout(WIDTH, HEIGHT, [], _png(Image.new("RGB", (WIDTH, HEIGHT), "white")), "")


async def _text_pages(**changes: int) -> list[PageLayout]:
    pdf = make_pdf(LINES, size=(WIDTH, HEIGHT), **changes)
    return (await LocalPdfLayoutExtractor().extract_layout(pdf)).pages


def test_constants_are_the_planned_ones() -> None:
    assert (TARGET_SCORE, MAX_FIX_PASSES) == (85, 3)
    assert (W_INK, W_TEXT, W_COLOR) == (0.45, 0.35, 0.20)


def test_identical_layouts_score_100() -> None:
    page = cv_page()
    sim = similarity([page], [page])
    assert sim.score == 100 and (sim.ink, sim.text, sim.color) == (1.0, 1.0, 1.0)
    assert describe(sim) == ""


def test_blank_render_scores_low() -> None:
    sim = similarity([cv_page()], [blank_page()])
    assert sim.score < 30 and sim.ink == 0 and sim.text == 0 and sim.color == 0
    assert "en moins" in describe(sim)


def test_wider_left_column_is_described() -> None:
    sim = similarity([cv_page(left=0.30)], [cv_page(left=0.45)])
    assert 30 < sim.score < 100
    text = describe(sim)
    assert "gauche" in text and "d'encre en plus à gauche que l'original." in text
    assert sim.shifts == {"haut": 0, "milieu": 0, "bas": 0} and "décalé" not in text
    left = next(zone for zone in sim.zones if zone.zone == "gauche")
    assert left.render > left.original


@pytest.mark.parametrize("shift", [1, 2, 3])
async def test_small_shift_still_reaches_target(shift: int) -> None:
    """Police substituée, moteur de rendu : quelques points de décalage restent « fidèles »."""
    sim = similarity(await _text_pages(), await _text_pages(top=72 + shift))
    assert sim.score >= TARGET_SCORE, sim


async def test_line_spacing_gap_stays_under_target_and_is_described() -> None:
    """Interligne 15 au lieu de 14 sur une page pleine : un vrai écart, sous la cible, dit."""
    sim = similarity(await _text_pages(), await _text_pages(leading=15))
    assert sim.score < TARGET_SCORE
    text = describe(sim)
    assert text.startswith(("L'encre du rendu ne recouvre", "Les blocs de texte du rendu"))
    assert "surtout" in text


async def test_large_shift_is_described() -> None:
    sim = similarity(await _text_pages(), await _text_pages(top=84))
    assert sim.score < TARGET_SCORE and describe(sim) != ""


@pytest.mark.parametrize(("top", "way"), [(80, "vers le bas"), (64, "vers le haut")])
async def test_vertical_shift_is_described_with_its_direction(top: int, way: str) -> None:
    """Revue 6.4, round 2, R3 : un décalage de 8 pt est dit avec son sens, son ampleur et la
    piste de la marge haute, en plus de la zone du recouvrement le plus faible."""
    sim = similarity(await _text_pages(), await _text_pages(top=top))
    assert sim.shifts == {"haut": top - 72, "milieu": top - 72, "bas": top - 72}, sim.shifts
    text = describe(sim)
    assert f"décalé {way} d'environ 8 pt dès le haut de la page : revoir la marge haute" in text


async def test_growing_shift_points_to_line_spacing() -> None:
    """Interligne 15 au lieu de 14 : le décalage grandit en descendant ; la phrase nomme le tiers
    où il est le plus fort et l'interligne."""
    sim = similarity(await _text_pages(), await _text_pages(leading=15))
    assert abs(sim.shifts["haut"]) < SHIFT_MIN_PT < sim.shifts["bas"], sim.shifts
    text = describe(sim)
    assert "décalé vers le bas d'au moins 30 pt, surtout en bas" in text
    assert "revoir l'interligne" in text


def test_missing_page_counts() -> None:
    sim = similarity([cv_page(), cv_page()], [cv_page()])
    assert (sim.pages_original, sim.pages_render) == (2, 1)
    assert sim.ink < 0.6 and "Pages : 1 au lieu de 2." in describe(sim)
    assert describe(sim).endswith("Le rendu doit garder le nombre de pages de l'original.")


def test_page_count_gap_caps_score_under_target() -> None:
    """Une page de débordement presque vide : le reste est identique, la cible reste manquée."""
    overflow = PageLayout(WIDTH, HEIGHT, [_block(60, 60, 200, 70)], blank_page().image_png, "")
    sim = similarity([cv_page()], [cv_page(), overflow])
    assert sim.score == TARGET_SCORE - 1 and "Pages : 2 au lieu de 1." in describe(sim)


def test_color_mismatch_lowers_color_part_and_names_the_accent() -> None:
    same = similarity([cv_page()], [cv_page()])
    other = similarity([cv_page()], [cv_page(accent=RED)])
    assert other.ink == same.ink == 1.0 and other.text == 1.0
    assert other.color < 0.9 and other.score < same.score
    assert other.accent_differs and not same.accent_differs
    assert "La couleur d'accent du rendu diffère de celle de l'original." in describe(other)


def test_describe_keeps_four_largest_gaps_over_five_points() -> None:
    zones = [
        ZoneDiff("haut", 0.50, 0.30),
        ZoneDiff("milieu", 0.50, 0.53),  # 3 points : omis
        ZoneDiff("bas", 0.10, 0.40),
        ZoneDiff("gauche", 0.60, 0.18),
        ZoneDiff("droite", 0.20, 0.27),
    ]
    zone_sentences = (
        "Le rendu a 42 % d'encre en moins à gauche que l'original. "
        "Le rendu a 30 % d'encre en plus en bas que l'original. "
        "Le rendu a 20 % d'encre en moins en haut que l'original. "
        "Le rendu a 7 % d'encre en plus à droite que l'original."
    )
    assert describe(Similarity(90, 0.9, 0.9, 0.9, 1, 1, zones)) == zone_sentences
    # Sous la cible : la composante la plus faible d'abord.
    assert describe(Similarity(70, 0.6, 0.5, 0.9, 1, 1, zones)) == (
        "Les blocs de texte du rendu ne recouvrent ceux de l'original qu'à 50 %. " + zone_sentences
    )


def test_describe_under_target_always_says_something() -> None:
    weak_color = Similarity(80, 1.0, 1.0, 0.3, 1, 1, [])
    assert describe(weak_color) == (
        "Les couleurs du rendu s'écartent de celles de l'original (ressemblance de 30 %)."
    )


def test_invisible_blocks_do_not_count_as_text() -> None:
    page = cv_page()
    trap = TextBlock("piège", 10, 800, 200, 801, "Lato", 1, "#ffffff", False, True)
    with_trap = PageLayout(WIDTH, HEIGHT, [*page.blocks, trap], page.image_png, "")
    assert similarity([page], [with_trap]).text == 1.0


def test_blocks_outside_the_page_are_bounded() -> None:
    """Un bloc visible hors du repère ne marque pas toute la page comme du texte."""
    page = blank_page()
    stray = PageLayout(WIDTH, HEIGHT, [_block(-50, -40, -10, -8)], page.image_png, "")
    assert similarity([page], [stray]).text == 1.0


def test_image_outside_the_page_frame_is_refused() -> None:
    page = cv_page()
    double = Image.new("RGB", (2 * WIDTH, 2 * HEIGHT), "white")
    at_144_dpi = PageLayout(WIDTH, HEIGHT, page.blocks, _png(double), "")
    with pytest.raises(ValueError, match="72 dpi"):
        similarity([page], [at_144_dpi])


def test_empty_documents_are_identical() -> None:
    sim = similarity([blank_page()], [blank_page()])
    assert sim.score == 100 and sim.zones and all(z.original == z.render == 0 for z in sim.zones)
