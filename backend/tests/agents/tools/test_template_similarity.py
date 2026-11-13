"""Score de ressemblance entre l'original et le rendu d'un gabarit (6.4, D120), sur des pages
fictives dessinées par le test (72 dpi : 1 pixel = 1 point)."""

import io

from PIL import Image, ImageDraw

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

WIDTH, HEIGHT = 595, 842
BLUE = (33, 84, 154)
RED = (190, 30, 30)
INK = (34, 34, 34)


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
    left = next(zone for zone in sim.zones if zone.zone == "gauche")
    assert left.render > left.original


def test_missing_page_counts() -> None:
    sim = similarity([cv_page(), cv_page()], [cv_page()])
    assert (sim.pages_original, sim.pages_render) == (2, 1)
    assert sim.ink < 0.6 and "Pages : 1 au lieu de 2." in describe(sim)
    assert describe(sim).endswith("Pages : 1 au lieu de 2.")


def test_color_mismatch_lowers_color_part() -> None:
    same = similarity([cv_page()], [cv_page()])
    other = similarity([cv_page()], [cv_page(accent=RED)])
    assert other.ink == same.ink == 1.0 and other.text == 1.0
    assert other.color < 0.9 and other.score < same.score


def test_describe_keeps_four_largest_gaps_over_five_points() -> None:
    zones = [
        ZoneDiff("haut", 0.50, 0.30),
        ZoneDiff("milieu", 0.50, 0.53),  # 3 points : omis
        ZoneDiff("bas", 0.10, 0.40),
        ZoneDiff("gauche", 0.60, 0.18),
        ZoneDiff("droite", 0.20, 0.27),
    ]
    sim = Similarity(70, 0.5, 0.5, 0.9, 1, 1, zones)
    assert describe(sim) == (
        "Le rendu a 42 % d'encre en moins à gauche que l'original. "
        "Le rendu a 30 % d'encre en plus en bas que l'original. "
        "Le rendu a 20 % d'encre en moins en haut que l'original. "
        "Le rendu a 7 % d'encre en plus à droite que l'original."
    )


def test_invisible_blocks_do_not_count_as_text() -> None:
    page = cv_page()
    trap = TextBlock("piège", 10, 800, 200, 801, "Lato", 1, "#ffffff", False, True)
    with_trap = PageLayout(WIDTH, HEIGHT, [*page.blocks, trap], page.image_png, "")
    assert similarity([page], [with_trap]).text == 1.0


def test_empty_documents_are_identical() -> None:
    sim = similarity([blank_page()], [blank_page()])
    assert sim.score == 100 and sim.zones and all(z.original == z.render == 0 for z in sim.zones)
