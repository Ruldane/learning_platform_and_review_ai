"""Grilles et couleurs d'une page de CV pour le score de ressemblance (`template_similarity`,
D120) : image à 72 dpi (1 pixel = 1 point, origine en haut à gauche), blocs de texte dans le même
repère que l'image et que `width_pt` / `height_pt` (CropBox, D119)."""

import io
import math
from collections import Counter
from collections.abc import Sequence
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray
from PIL import Image

from app.providers.pdf.base import PageLayout

GRID_PT = 4
INK_LUMA = 200
# Couleurs : 32 niveaux par canal ; quasi-blanc (tous les canaux ≥ 240) exclu.
COLOR_LEVELS = 32
NEAR_WHITE = 240
# Couleur d'accent : la plus fréquente dont les canaux s'écartent d'au moins 48 (pas un gris).
ACCENT_MIN_SPREAD = 48
# 4 couleurs dominantes de l'original, comparées aux 8 dominantes du rendu ; distance RVB maximale ;
# couleur d'accent différente au-delà de 60.
ORIGINAL_COLORS = 4
RENDER_COLORS = 8
MAX_DISTANCE = 441.7
ACCENT_MAX_DISTANCE = 60
# Écart d'image toléré (arrondi du rendu) entre la taille de l'image et celle de la page.
_SIZE_SLACK_PX = 1

Zone = Literal["haut", "milieu", "bas", "gauche", "droite"]
ZONES: tuple[Zone, ...] = ("haut", "milieu", "bas", "gauche", "droite")
Grid = NDArray[np.bool_]
Rgb = tuple[int, int, int]


def page_shape(page: PageLayout) -> tuple[int, int]:
    return math.ceil(page.height_pt / GRID_PT), math.ceil(page.width_pt / GRID_PT)


def _image(page: PageLayout, mode: str) -> NDArray[np.uint8]:
    """Pixels de l'image de la page ; `ValueError` si sa taille n'est pas celle de la page à
    72 dpi (autre résolution, autre repère : la comparer couperait ou étirerait sans le dire)."""
    with Image.open(io.BytesIO(page.image_png)) as image:
        width, height = image.size
        if (
            abs(width - page.width_pt) > _SIZE_SLACK_PX
            or abs(height - page.height_pt) > _SIZE_SLACK_PX
        ):
            raise ValueError("image de page hors du repère de la page (72 dpi attendus)")
        pixels: NDArray[np.uint8] = np.asarray(image.convert(mode))
    return pixels


def ink_grid(page: PageLayout, shape: tuple[int, int]) -> Grid:
    """Cellules de `GRID_PT` points qui ont au moins un pixel de luminance < `INK_LUMA`."""
    rows, cols = shape
    dark = _image(page, "L") < INK_LUMA
    padded = np.zeros((rows * GRID_PT, cols * GRID_PT), dtype=np.bool_)
    height, width = min(dark.shape[0], padded.shape[0]), min(dark.shape[1], padded.shape[1])
    padded[:height, :width] = dark[:height, :width]
    grid: Grid = padded.reshape(rows, GRID_PT, cols, GRID_PT).any(axis=(1, 3))
    return grid


def _cells(start: float, end: float, size: int) -> tuple[int, int]:
    """Cellules [début, fin[ couvertes par [start, end] points, bornées à la grille."""
    low = min(size, max(0, math.floor(start / GRID_PT)))
    high = min(size, max(0, math.ceil(end / GRID_PT)))
    return low, max(low, high)


def text_grid(page: PageLayout, shape: tuple[int, int]) -> Grid:
    """Cellules couvertes par les blocs de texte visibles, bornées à la page."""
    rows, cols = shape
    grid = np.zeros(shape, dtype=np.bool_)
    for block in page.blocks:
        if block.invisible:
            continue
        top, bottom = _cells(block.top, block.bottom, rows)
        left, right = _cells(block.x0, block.x1, cols)
        grid[top:bottom, left:right] = True
    return grid


def dilate(grid: Grid) -> Grid:
    """La grille élargie d'une cellule dans chaque direction (voisinage 3 × 3)."""
    rows, cols = grid.shape
    padded = np.pad(grid, 1)
    out = np.zeros_like(grid)
    for dy in range(3):
        for dx in range(3):
            out |= padded[dy : dy + rows, dx : dx + cols]
    return out


def zone_views(grid: NDArray[Any]) -> dict[Zone, NDArray[Any]]:
    """Tiers haut, milieu, bas ; moitiés gauche, droite."""
    rows, cols = grid.shape
    return {
        "haut": grid[: rows // 3],
        "milieu": grid[rows // 3 : 2 * rows // 3],
        "bas": grid[2 * rows // 3 :],
        "gauche": grid[:, : cols // 2],
        "droite": grid[:, cols // 2 :],
    }


def palette(pages: Sequence[PageLayout]) -> Counter[Rgb]:
    """Couleurs quantifiées sur `COLOR_LEVELS` niveaux (centre de chaque niveau), quasi-blanc
    exclu, comptées en pixels sur toutes les pages."""
    step = 256 // COLOR_LEVELS
    counts: Counter[Rgb] = Counter()
    for page in pages:
        pixels = _image(page, "RGB").reshape(-1, 3).astype(np.int32)
        quantized = pixels // step * step + step // 2
        kept = quantized[~(quantized >= NEAR_WHITE).all(axis=1)]
        colors, numbers = np.unique(kept, axis=0, return_counts=True)
        for color, number in zip(colors.tolist(), numbers.tolist(), strict=True):
            counts[(color[0], color[1], color[2])] += number
    return counts


def accent(counts: Counter[Rgb]) -> Rgb | None:
    """La couleur non grise la plus fréquente (`None` : page en noir, gris et blanc)."""
    for color, _ in counts.most_common():
        if max(color) - min(color) >= ACCENT_MIN_SPREAD:
            return color
    return None


def color_match(original: Counter[Rgb], render: Counter[Rgb]) -> float:
    """1 − distance moyenne (pondérée par fréquence) des `ORIGINAL_COLORS` couleurs dominantes
    de l'original à la plus proche des `RENDER_COLORS` dominantes du rendu, divisée par
    `MAX_DISTANCE`. Original sans couleur : 1 ; rendu sans couleur (et original coloré) : 0."""
    dominant = original.most_common(ORIGINAL_COLORS)
    if not dominant:
        return 1.0
    candidates = [color for color, _ in render.most_common(RENDER_COLORS)]
    if not candidates:
        return 0.0
    total = sum(number for _, number in dominant)
    distance = sum(
        number / total * min(math.dist(color, candidate) for candidate in candidates)
        for color, number in dominant
    )
    return max(0.0, 1.0 - distance / MAX_DISTANCE)


def accent_differs(original: Counter[Rgb], render: Counter[Rgb]) -> bool:
    """La couleur d'accent de l'original manque au rendu ou s'en écarte de plus de
    `ACCENT_MAX_DISTANCE`."""
    accent_o, accent_r = accent(original), accent(render)
    if accent_o is None:
        return False
    return accent_r is None or math.dist(accent_o, accent_r) > ACCENT_MAX_DISTANCE
