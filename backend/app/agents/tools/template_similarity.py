"""Score de ressemblance entre le CV d'origine et le rendu de son gabarit (SPEC 5.2 : « fidèle, pas
identique au pixel » ; D120). Trois parts sur une grille de `GRID_PT` points : l'encre (cellules
qui ont un pixel sombre), les boîtes de texte et les couleurs dominantes. Les écarts d'encre par
zone sont dits au Maquettiste en phrases françaises (`describe`).

Module pur (images des pages à 72 dpi : 1 pixel = 1 point, origine en haut à gauche), partagé par
le Maquettiste (6.9) et les gabarits (6.10) : il vit dans `agents/tools` car le moteur n'importe
aucune feature (contrat 6)."""

import io
import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
from numpy.typing import NDArray
from PIL import Image

from app.providers.pdf.base import PageLayout

GRID_PT = 4
INK_LUMA = 200
TARGET_SCORE = 85
MAX_FIX_PASSES = 3
W_INK, W_TEXT, W_COLOR = 0.45, 0.35, 0.20
# Couleurs : 32 niveaux par canal ; quasi-blanc (tous les canaux ≥ 240) exclu ; 4 couleurs
# dominantes de l'original, comparées aux 8 dominantes du rendu ; distance RVB maximale.
COLOR_LEVELS = 32
NEAR_WHITE = 240
ORIGINAL_COLORS = 4
RENDER_COLORS = 8
MAX_DISTANCE = 441.7
# Description : écarts de plus de 5 points seulement, 4 phrases au plus.
ZONE_THRESHOLD = 5
MAX_ZONE_SENTENCES = 4

Zone = Literal["haut", "milieu", "bas", "gauche", "droite"]
_ZONE_WORDS: dict[Zone, str] = {
    "haut": "en haut",
    "milieu": "au milieu",
    "bas": "en bas",
    "gauche": "à gauche",
    "droite": "à droite",
}
Grid = NDArray[np.bool_]


@dataclass(frozen=True)
class ZoneDiff:
    """Part d'encre (0 à 1 : cellules encrées / cellules de la zone, toutes pages) d'une zone :
    tiers haut, milieu, bas ; moitiés gauche, droite."""

    zone: Zone
    original: float
    render: float


@dataclass(frozen=True)
class Similarity:
    score: int
    ink: float
    text: float
    color: float
    pages_original: int
    pages_render: int
    zones: list[ZoneDiff]


def _shape(page: PageLayout) -> tuple[int, int]:
    return math.ceil(page.height_pt / GRID_PT), math.ceil(page.width_pt / GRID_PT)


def _ink(page: PageLayout, shape: tuple[int, int]) -> Grid:
    """Cellules de la grille qui ont au moins un pixel de luminance < `INK_LUMA`."""
    rows, cols = shape
    with Image.open(io.BytesIO(page.image_png)) as image:
        dark = np.asarray(image.convert("L")) < INK_LUMA
    padded = np.zeros((rows * GRID_PT, cols * GRID_PT), dtype=np.bool_)
    height, width = min(dark.shape[0], padded.shape[0]), min(dark.shape[1], padded.shape[1])
    padded[:height, :width] = dark[:height, :width]
    grid: Grid = padded.reshape(rows, GRID_PT, cols, GRID_PT).any(axis=(1, 3))
    return grid


def _text(page: PageLayout, shape: tuple[int, int]) -> Grid:
    """Cellules couvertes par les blocs de texte visibles."""
    grid = np.zeros(shape, dtype=np.bool_)
    for block in page.blocks:
        if block.invisible:
            continue
        top, left = max(0, math.floor(block.top / GRID_PT)), max(0, math.floor(block.x0 / GRID_PT))
        bottom, right = math.ceil(block.bottom / GRID_PT), math.ceil(block.x1 / GRID_PT)
        grid[top:bottom, left:right] = True
    return grid


def _grids(original: PageLayout | None, render: PageLayout | None) -> tuple[Grid, Grid, Grid, Grid]:
    """Encre et texte de l'original et du rendu sur une même grille (page absente : vide)."""
    shapes = [_shape(page) for page in (original, render) if page is not None]
    shape = (max(s[0] for s in shapes), max(s[1] for s in shapes))
    empty = np.zeros(shape, dtype=np.bool_)
    return (
        _ink(original, shape) if original else empty,
        _ink(render, shape) if render else empty,
        _text(original, shape) if original else empty,
        _text(render, shape) if render else empty,
    )


def _zones(grid: Grid) -> dict[Zone, Grid]:
    rows, cols = grid.shape
    return {
        "haut": grid[: rows // 3],
        "milieu": grid[rows // 3 : 2 * rows // 3],
        "bas": grid[2 * rows // 3 :],
        "gauche": grid[:, : cols // 2],
        "droite": grid[:, cols // 2 :],
    }


@dataclass
class _Tally:
    ink_inter: int = 0
    ink_union: int = 0
    text_inter: int = 0
    text_union: int = 0
    zone_cells: Counter[Zone] = field(default_factory=Counter)
    zone_original: Counter[Zone] = field(default_factory=Counter)
    zone_render: Counter[Zone] = field(default_factory=Counter)

    def add(self, ink_o: Grid, ink_r: Grid, text_o: Grid, text_r: Grid) -> None:
        self.ink_inter += int((ink_o & ink_r).sum())
        self.ink_union += int((ink_o | ink_r).sum())
        self.text_inter += int((text_o & text_r).sum())
        self.text_union += int((text_o | text_r).sum())
        render_zones = _zones(ink_r)
        for zone, cells in _zones(ink_o).items():
            self.zone_cells[zone] += cells.size
            self.zone_original[zone] += int(cells.sum())
            self.zone_render[zone] += int(render_zones[zone].sum())

    def zones(self) -> list[ZoneDiff]:
        return [
            ZoneDiff(
                zone=zone,
                original=self.zone_original[zone] / cells if cells else 0.0,
                render=self.zone_render[zone] / cells if cells else 0.0,
            )
            for zone, cells in self.zone_cells.items()
        ]


def _iou(inter: int, union: int) -> float:
    return inter / union if union else 1.0


def _palette(pages: Sequence[PageLayout]) -> Counter[tuple[int, int, int]]:
    """Couleurs quantifiées sur `COLOR_LEVELS` niveaux (centre de chaque niveau), quasi-blanc
    exclu, comptées en pixels sur toutes les pages."""
    step = 256 // COLOR_LEVELS
    counts: Counter[tuple[int, int, int]] = Counter()
    for page in pages:
        with Image.open(io.BytesIO(page.image_png)) as image:
            pixels = np.asarray(image.convert("RGB")).reshape(-1, 3).astype(np.int32)
        quantized = pixels // step * step + step // 2
        kept = quantized[~(quantized >= NEAR_WHITE).all(axis=1)]
        colors, numbers = np.unique(kept, axis=0, return_counts=True)
        for color, number in zip(colors.tolist(), numbers.tolist(), strict=True):
            counts[(color[0], color[1], color[2])] += number
    return counts


def _color(original: Sequence[PageLayout], render: Sequence[PageLayout]) -> float:
    """1 − distance moyenne (pondérée par fréquence) des couleurs dominantes de l'original à la
    plus proche des dominantes du rendu, divisée par `MAX_DISTANCE`. Original sans couleur : 1 ;
    rendu sans couleur (et original coloré) : 0."""
    dominant = _palette(original).most_common(ORIGINAL_COLORS)
    if not dominant:
        return 1.0
    candidates = [color for color, _ in _palette(render).most_common(RENDER_COLORS)]
    if not candidates:
        return 0.0
    total = sum(number for _, number in dominant)
    distance = sum(
        number / total * min(math.dist(color, candidate) for candidate in candidates)
        for color, number in dominant
    )
    return max(0.0, 1.0 - distance / MAX_DISTANCE)


def similarity(original: Sequence[PageLayout], render: Sequence[PageLayout]) -> Similarity:
    """Pages appariées par rang (page absente : grille vide) ; encre et texte : IoU des cellules
    sur toutes les pages (aucune cellule des deux côtés : 1) ; score arrondi au plus proche."""
    tally = _Tally()
    for index in range(max(len(original), len(render))):
        page_o = original[index] if index < len(original) else None
        page_r = render[index] if index < len(render) else None
        tally.add(*_grids(page_o, page_r))
    ink = _iou(tally.ink_inter, tally.ink_union)
    text = _iou(tally.text_inter, tally.text_union)
    color = _color(original, render)
    raw = 100 * (W_INK * ink + W_TEXT * text + W_COLOR * color)
    return Similarity(
        score=min(100, max(0, math.floor(raw + 0.5))),
        ink=ink,
        text=text,
        color=color,
        pages_original=len(original),
        pages_render=len(render),
        zones=tally.zones(),
    )


def describe(sim: Similarity) -> str:
    """Phrases pour le Maquettiste : les zones dont la part d'encre diffère de plus de
    `ZONE_THRESHOLD` points (les plus grands écarts d'abord, `MAX_ZONE_SENTENCES` au plus), puis
    le nombre de pages s'il diffère. Chaîne vide si rien n'est à signaler."""
    gaps = sorted(
        ((round(100 * (zone.render - zone.original)), zone.zone) for zone in sim.zones),
        key=lambda gap: -abs(gap[0]),
    )
    sentences = [
        f"Le rendu a {abs(points)} % d'encre en {'plus' if points > 0 else 'moins'} "
        f"{_ZONE_WORDS[zone]} que l'original."
        for points, zone in gaps
        if abs(points) > ZONE_THRESHOLD
    ][:MAX_ZONE_SENTENCES]
    if sim.pages_render != sim.pages_original:
        sentences.append(f"Pages : {sim.pages_render} au lieu de {sim.pages_original}.")
    return " ".join(sentences)
