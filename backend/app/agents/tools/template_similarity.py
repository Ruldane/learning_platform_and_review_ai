"""Score the resemblance between a CV and its rendered template (SPEC 5.2, D120).

Compare ink coverage, text boxes, and dominant colors on a grid. Allow one cell of
tolerance in the ink and text overlap so small rendering shifts have less impact.
`describe` explains the largest differences to the Layout Designer. Both the agent
and the template feature use this module.
"""

import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np

from app.agents.tools.template_grids import (
    GRID_PT,
    INK_LUMA,
    SHIFT_MAX_PT,
    SHIFT_MIN_PT,
    ZONES,
    Grid,
    ShiftCosts,
    Zone,
    accent_differs,
    color_match,
    dilate,
    ink_grid,
    page_shape,
    palette,
    text_grid,
    zone_views,
)
from app.providers.pdf.base import PageLayout

__all__ = [
    "GRID_PT",
    "INK_LUMA",
    "MAX_FIX_PASSES",
    "TARGET_SCORE",
    "W_COLOR",
    "W_INK",
    "W_TEXT",
    "Similarity",
    "Zone",
    "ZoneDiff",
    "ZoneMatch",
    "describe",
    "similarity",
]

TARGET_SCORE = 85
MAX_FIX_PASSES = 3
W_INK, W_TEXT, W_COLOR = 0.45, 0.35, 0.20
# Report up to four region differences larger than five percentage points.
ZONE_THRESHOLD = 5
MAX_ZONE_SENTENCES = 4
TOLERANT_SHARE = 0.5  # Weight of the tolerance-adjusted ink and text overlap (D120).
_FULL = 0.99  # Treat scores of 99% or more as fully matched.

_ZONE_WORDS: dict[Zone, str] = {
    "top": "at the top",
    "middle": "in the middle",
    "bottom": "at the bottom",
    "left": "on the left",
    "right": "on the right",
}


@dataclass(frozen=True)
class ZoneDiff:
    """Share of inked cells in a region across all pages."""

    zone: Zone
    original: float
    render: float


@dataclass(frozen=True)
class ZoneMatch:
    """Ink and text overlap scores in a region, from 0 to 1."""

    zone: Zone
    ink: float
    text: float


@dataclass(frozen=True)
class Similarity:
    """Comparison with a score below the target when the page counts differ.

    `shifts` reports vertical offsets in points per page third, positive downward.
    """

    score: int
    ink: float
    text: float
    color: float
    pages_original: int
    pages_render: int
    zones: list[ZoneDiff]
    matches: list[ZoneMatch] = field(default_factory=list)
    accent_differs: bool = False
    shifts: dict[Zone, int] = field(default_factory=dict)


@dataclass
class _Overlap:
    """Track tolerance-adjusted overlap and strict intersection-over-union by region."""

    hit: Counter[Zone | None] = field(default_factory=Counter)
    total: Counter[Zone | None] = field(default_factory=Counter)
    inter: Counter[Zone | None] = field(default_factory=Counter)
    union: Counter[Zone | None] = field(default_factory=Counter)

    def add(self, first: Grid, second: Grid) -> None:
        hits = (first & dilate(second)).astype(np.int32) + (second & dilate(first)).astype(np.int32)
        grids = {
            "hit": hits,
            "total": first.astype(np.int32) + second.astype(np.int32),
            "inter": first & second,
            "union": first | second,
        }
        for name, grid in grids.items():
            counter: Counter[Zone | None] = getattr(self, name)
            counter[None] += int(grid.sum())
            for zone, view in zone_views(grid).items():
                counter[zone] += int(view.sum())

    def ratio(self, zone: Zone | None = None) -> float:
        """Average the two overlap scores. Two empty regions match fully."""
        tolerant = self.hit[zone] / self.total[zone] if self.total[zone] else 1.0
        strict = self.inter[zone] / self.union[zone] if self.union[zone] else 1.0
        return TOLERANT_SHARE * tolerant + (1 - TOLERANT_SHARE) * strict


@dataclass
class _Tally:
    ink: _Overlap = field(default_factory=_Overlap)
    text: _Overlap = field(default_factory=_Overlap)
    cells: Counter[Zone] = field(default_factory=Counter)
    original: Counter[Zone] = field(default_factory=Counter)
    render: Counter[Zone] = field(default_factory=Counter)
    shift: ShiftCosts = field(default_factory=ShiftCosts)

    def add(self, page_o: PageLayout | None, page_r: PageLayout | None) -> None:
        shapes = [page_shape(page) for page in (page_o, page_r) if page is not None]
        shape = (max(s[0] for s in shapes), max(s[1] for s in shapes))
        if page_o is not None and page_r is not None:
            self.shift.add(page_o, page_r, shape[0] * GRID_PT)
        ink_o, ink_r, text_o, text_r = (
            grid(page, shape) if page is not None else np.zeros(shape, dtype=np.bool_)
            for grid, page in (
                (ink_grid, page_o),
                (ink_grid, page_r),
                (text_grid, page_o),
                (text_grid, page_r),
            )
        )
        self.ink.add(ink_o, ink_r)
        self.text.add(text_o, text_r)
        render_zones = zone_views(ink_r)
        for zone, cells in zone_views(ink_o).items():
            self.cells[zone] += cells.size
            self.original[zone] += int(cells.sum())
            self.render[zone] += int(render_zones[zone].sum())

    def zones(self) -> list[ZoneDiff]:
        return [
            ZoneDiff(
                zone=zone,
                original=self.original[zone] / self.cells[zone] if self.cells[zone] else 0.0,
                render=self.render[zone] / self.cells[zone] if self.cells[zone] else 0.0,
            )
            for zone in ZONES
        ]

    def matches(self) -> list[ZoneMatch]:
        return [ZoneMatch(zone, self.ink.ratio(zone), self.text.ratio(zone)) for zone in ZONES]


def similarity(original: Sequence[PageLayout], render: Sequence[PageLayout]) -> Similarity:
    """Compare pages in order, using a blank grid for a missing page.

    Round the overall score and keep it below the target if the page counts differ.
    Invalid image dimensions at 72 dpi raise `ValueError`.
    """
    tally = _Tally()
    for index in range(max(len(original), len(render))):
        page_o = original[index] if index < len(original) else None
        page_r = render[index] if index < len(render) else None
        tally.add(page_o, page_r)
    ink, text = tally.ink.ratio(), tally.text.ratio()
    palette_o, palette_r = palette(original), palette(render)
    color = color_match(palette_o, palette_r)
    score = min(
        100, max(0, math.floor(100 * (W_INK * ink + W_TEXT * text + W_COLOR * color) + 0.5))
    )
    if len(original) != len(render):
        score = min(score, TARGET_SCORE - 1)
    return Similarity(
        score=score,
        ink=ink,
        text=text,
        color=color,
        pages_original=len(original),
        pages_render=len(render),
        zones=tally.zones(),
        matches=tally.matches(),
        accent_differs=accent_differs(palette_o, palette_r),
        shifts=tally.shift.shifts(),
    )


def _weakest(sim: Similarity) -> str | None:
    """Describe the weakest component and region when the score is below 99%."""
    parts = {"ink": sim.ink, "text": sim.text, "color": sim.color}
    name = min(parts, key=lambda key: parts[key])
    value = parts[name]
    if value >= _FULL:
        return None
    percent = math.floor(100 * value)
    if name == "color":
        return f"The rendered colors differ from the original ({percent}% similarity)."
    lead = "Rendered ink overlaps" if name == "ink" else "Rendered text boxes overlap"
    sentence = f"{lead} the original by {percent}%"
    if sim.matches:
        zone = min(sim.matches, key=lambda match: getattr(match, name)).zone
        sentence += f", with the largest difference {_ZONE_WORDS[zone]}"
    return sentence + "."


def _shift_sentence(shifts: dict[Zone, int]) -> str | None:
    """Describe the largest vertical shift and which layout settings could account for it."""
    if not shifts:
        return None
    # For equal shifts, prefer the lower affected region.
    zone, points = max(reversed(list(shifts.items())), key=lambda item: abs(item[1]))
    if abs(points) < SHIFT_MIN_PT:
        return None
    amount = "at least" if abs(points) >= SHIFT_MAX_PT else "about"
    direction = "down" if points > 0 else "up"
    sentence = f"The rendered content shifts {direction} by {amount} {abs(points)} pt"
    if zone == "top" or abs(points - shifts.get("top", 0)) < SHIFT_MIN_PT:
        return f"{sentence} from the top of the page. Check the top margin or header."
    return (
        f"{sentence}, mainly {_ZONE_WORDS[zone]}. The gap grows down the page. "
        "Check line spacing or gaps between blocks."
    )


def describe(sim: Similarity) -> str:
    """Describe the significant differences for the Layout Designer."""
    sentences: list[str] = []
    weakest = _weakest(sim) if sim.score < TARGET_SCORE else None
    if weakest:
        sentences.append(weakest)
    shift = _shift_sentence(sim.shifts)
    if shift:
        sentences.append(shift)
    if sim.accent_differs:
        sentences.append("The rendered accent color differs from the original.")
    gaps = sorted(
        ((round(100 * (zone.render - zone.original)), zone.zone) for zone in sim.zones),
        key=lambda gap: -abs(gap[0]),
    )
    sentences += [
        f"The render has {abs(points)}% {'more' if points > 0 else 'less'} ink "
        f"{_ZONE_WORDS[zone]} than the original."
        for points, zone in gaps
        if abs(points) > ZONE_THRESHOLD
    ][:MAX_ZONE_SENTENCES]
    if sim.pages_render != sim.pages_original:
        sentences.append(f"The page count changed from {sim.pages_original} to {sim.pages_render}.")
        sentences.append("Match the original page count.")
    return " ".join(sentences)
