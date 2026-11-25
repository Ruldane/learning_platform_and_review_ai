"""Page grids and colors for CV template comparison (D119, D120).

At 72 dpi, one pixel corresponds to one point. Text blocks and image dimensions
share the CropBox coordinates, with the origin in the top-left corner.
"""

import io
import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray
from PIL import Image

from app.providers.pdf.base import PageLayout

GRID_PT = 4
INK_LUMA = 200
# Quantize each color channel and exclude near-white pixels.
COLOR_LEVELS = 32
NEAR_WHITE = 240
# The accent is the most common color with sufficient spread between channel values.
ACCENT_MIN_SPREAD = 48
# Compare four dominant original colors against eight dominant rendered colors.
ORIGINAL_COLORS = 4
RENDER_COLORS = 8
MAX_DISTANCE = 441.7
ACCENT_MAX_DISTANCE = 60
# Tolerance for rounding page size during rasterization.
_SIZE_SLACK_PX = 1

# Find vertical shifts up to 30 points per third and report shifts of at least 3 points.
SHIFT_MAX_PT = 30
SHIFT_MIN_PT = 3
SHIFT_WINDOW_PT = 24

Zone = Literal["top", "middle", "bottom", "left", "right"]
ZONES: tuple[Zone, ...] = ("top", "middle", "bottom", "left", "right")
VERTICAL_ZONES: tuple[Zone, ...] = ("top", "middle", "bottom")
_LEGACY_ZONES = {
    "haut": "top",
    "milieu": "middle",
    "bas": "bottom",
    "gauche": "left",
    "droite": "right",
}
Grid = NDArray[np.bool_]
Rgb = tuple[int, int, int]


def zone_code(code: str) -> str:
    """Read the region code used in a saved comparison."""
    return _LEGACY_ZONES.get(code, code)


def page_shape(page: PageLayout) -> tuple[int, int]:
    return math.ceil(page.height_pt / GRID_PT), math.ceil(page.width_pt / GRID_PT)


def _image(page: PageLayout, mode: str) -> NDArray[np.uint8]:
    """Read pixels from a 72 dpi page image with the expected dimensions."""
    with Image.open(io.BytesIO(page.image_png)) as image:
        width, height = image.size
        if (
            abs(width - page.width_pt) > _SIZE_SLACK_PX
            or abs(height - page.height_pt) > _SIZE_SLACK_PX
        ):
            raise ValueError("Page image dimensions do not match the expected 72 dpi")
        pixels: NDArray[np.uint8] = np.asarray(image.convert(mode))
    return pixels


def ink_grid(page: PageLayout, shape: tuple[int, int]) -> Grid:
    """Mark each grid cell containing at least one pixel darker than `INK_LUMA`."""
    rows, cols = shape
    dark = _image(page, "L") < INK_LUMA
    padded = np.zeros((rows * GRID_PT, cols * GRID_PT), dtype=np.bool_)
    height, width = min(dark.shape[0], padded.shape[0]), min(dark.shape[1], padded.shape[1])
    padded[:height, :width] = dark[:height, :width]
    grid: Grid = padded.reshape(rows, GRID_PT, cols, GRID_PT).any(axis=(1, 3))
    return grid


def _cells(start: float, end: float, size: int) -> tuple[int, int]:
    """Convert a point interval to a half-open cell range clipped to the grid."""
    low = min(size, max(0, math.floor(start / GRID_PT)))
    high = min(size, max(0, math.ceil(end / GRID_PT)))
    return low, max(low, high)


def text_grid(page: PageLayout, shape: tuple[int, int]) -> Grid:
    """Mark cells covered by visible text blocks within the page."""
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
    """Expand each marked cell by one cell in every direction."""
    rows, cols = grid.shape
    padded = np.pad(grid, 1)
    out = np.zeros_like(grid)
    for dy in range(3):
        for dx in range(3):
            out |= padded[dy : dy + rows, dx : dx + cols]
    return out


def zone_views(grid: NDArray[Any]) -> dict[Zone, NDArray[Any]]:
    """Return the vertical thirds and horizontal halves of the grid."""
    rows, cols = grid.shape
    return {
        "top": grid[: rows // 3],
        "middle": grid[rows // 3 : 2 * rows // 3],
        "bottom": grid[2 * rows // 3 :],
        "left": grid[:, : cols // 2],
        "right": grid[:, cols // 2 :],
    }


def palette(pages: Sequence[PageLayout]) -> Counter[Rgb]:
    """Quantize colors and count non-white pixels by color across all pages."""
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
    """Return the most common non-gray color, if present."""
    for color, _ in counts.most_common():
        if max(color) - min(color) >= ACCENT_MIN_SPREAD:
            return color
    return None


def color_match(original: Counter[Rgb], render: Counter[Rgb]) -> float:
    """Score the frequency-weighted distance to each original color's nearest render color.

    An empty original palette scores 1. An empty render palette scores 0 otherwise.
    """
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
    """Report a missing or sufficiently different render accent."""
    accent_o, accent_r = accent(original), accent(render)
    if accent_o is None:
        return False
    return accent_r is None or math.dist(accent_o, accent_r) > ACCENT_MAX_DISTANCE


@dataclass
class ShiftCosts:
    """Sum row-profile differences across paired pages for each candidate shift per third.

    Positive shifts put the rendered text lower on the page.
    """

    costs: dict[Zone, NDArray[np.float64]] = field(default_factory=dict)

    def add(self, page_o: PageLayout, page_r: PageLayout, height: int) -> None:
        original, render = _text_rows(page_o, height), _text_rows(page_r, height)
        padded = np.pad(render, SHIFT_MAX_PT)
        cuts = (0, height // 3, 2 * height // 3, height)
        for index, zone in enumerate(VERTICAL_ZONES):
            low, high = cuts[index], cuts[index + 1]
            part = original[low:high]
            cost = np.array(
                [
                    np.abs(part - padded[low + SHIFT_MAX_PT + s : high + SHIFT_MAX_PT + s]).sum()
                    for s in range(-SHIFT_MAX_PT, SHIFT_MAX_PT + 1)
                ],
                dtype=np.float64,
            )
            self.costs[zone] = self.costs.get(zone, np.zeros_like(cost)) + cost

    def shifts(self) -> dict[Zone, int]:
        """Choose the lowest-cost shift per third, preferring smaller shifts on ties."""
        span = range(-SHIFT_MAX_PT, SHIFT_MAX_PT + 1)
        out: dict[Zone, int] = {}
        for zone, cost in self.costs.items():
            values = [float(value) for value in cost]
            out[zone] = min(span, key=lambda s: (values[s + SHIFT_MAX_PT], abs(s)))
        return out


def _text_rows(page: PageLayout, height: int) -> NDArray[np.float64]:
    """Build a normalized vertical profile of visible text block widths.

    The sliding sum reduces false matches between neighboring lines when spacing differs.
    Normalization avoids treating changes in font or column width as a vertical shift.
    """
    rows = np.zeros(height, dtype=np.float64)
    for block in page.blocks:
        if not block.invisible:
            top, bottom = _cells_pt(block.top, block.bottom, height)
            rows[top:bottom] += block.x1 - block.x0
    smoothed: NDArray[np.float64] = np.convolve(rows, np.ones(SHIFT_WINDOW_PT), "same")
    total = float(smoothed.sum())
    return smoothed / total if total > 0 else smoothed


def _cells_pt(start: float, end: float, size: int) -> tuple[int, int]:
    low = min(size, max(0, math.floor(start)))
    return low, max(low, min(size, math.ceil(end)))
