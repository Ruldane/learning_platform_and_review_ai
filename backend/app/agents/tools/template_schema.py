"""What the Designer writes: a description of a CV's design (`TemplateSpec`), never HTML or
CSS, which the code writes from it (D118). The colours, the fonts and the layout are checked by
`template_problems`, whose sentences are sent back to the model so that it corrects them.
"""

import re
from collections import Counter
from collections.abc import Collection
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.agents.tools.cv_schema import SectionKey

# The #rrggbb colour format is checked by `template_problems` (asked again, not refused).
_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
ColumnBlock = SectionKey | Literal["identity"]
Margin = Annotated[float, Field(ge=0, le=40)]


class PageSpec(BaseModel):
    width_pt: float = Field(ge=200, le=1000)
    height_pt: float = Field(ge=200, le=1400)
    margins_mm: tuple[Margin, Margin, Margin, Margin]  # top, right, bottom, left


class ColumnSpec(BaseModel):
    width_pct: int = Field(ge=15, le=100)
    background: str | None = Field(default=None, max_length=32)
    text_color: str | None = Field(default=None, max_length=32)
    sections: list[ColumnBlock] = Field(min_length=1, max_length=8)


class FontSpec(BaseModel):
    body: str = Field(max_length=60)
    heading: str = Field(max_length=60)
    body_pt: float = Field(ge=7, le=14)
    heading_pt: float = Field(ge=8, le=28)
    name_pt: float = Field(ge=12, le=40)
    line_height: float = Field(ge=1.0, le=1.8)


class TemplateSpec(BaseModel):
    page: PageSpec
    columns: list[ColumnSpec] = Field(min_length=1, max_length=2)
    fonts: FontSpec
    accent: str = Field(max_length=32)
    text: str = Field(max_length=32)
    muted: str = Field(max_length=32)
    header_band: str | None = Field(default=None, max_length=32)
    section_title: Literal["plain", "underline", "left_bar", "band"]
    uppercase_titles: bool
    dates: Literal["right", "below", "left"]
    bullets: Literal["dot", "dash", "none"]
    gap_mm: float = Field(ge=0, le=20)


class FontUse(BaseModel):
    """A font of a template (`cv_templates.fonts`): `family` is the free font used,
    `substitute` says it replaces the one of the original PDF (preflight G25)."""

    role: Literal["body", "heading"]
    family: str = Field(min_length=1, max_length=60)
    substitute: bool


def _layout_problems(spec: TemplateSpec) -> list[str]:
    problems: list[str] = []
    total = sum(column.width_pct for column in spec.columns)
    if total != 100:
        problems.append(f"The column widths total {total}%: they must total 100%.")
    counts = Counter(block for column in spec.columns for block in column.sections)
    if counts["identity"] != 1:
        problems.append(
            f"The “identity” block must appear exactly once (it appears "
            f"{counts['identity']} times)."
        )
    heads = {column.sections[0] for column in spec.columns}
    if spec.header_band is not None and counts["identity"] == 1 and "identity" not in heads:
        problems.append(
            "The band (“header_band”) carries the “identity” block: put “identity” at the "
            "head of a column, or remove the band."
        )
    for block, count in counts.items():
        if block != "identity" and count > 1:
            problems.append(
                f"The section “{block}” appears {count} times: place it only once, "
                "in a single column."
            )
    return problems


def _font_problems(spec: TemplateSpec, available_fonts: Collection[str]) -> list[str]:
    known = {font.casefold() for font in available_fonts}
    choices = ", ".join(sorted(available_fonts))
    return [
        f"The font “{family}” is not available: choose among {choices}."
        for family in dict.fromkeys((spec.fonts.body, spec.fonts.heading))
        if family.casefold() not in known
    ]


def _color_problems(spec: TemplateSpec) -> list[str]:
    colors: list[tuple[str, str | None]] = [
        ("accent", spec.accent),
        ("text", spec.text),
        ("muted", spec.muted),
        ("header_band", spec.header_band),
    ]
    for rank, column in enumerate(spec.columns, start=1):
        colors.append((f"column {rank}, background", column.background))
        colors.append((f"column {rank}, text_color", column.text_color))
    return [
        f"The colour “{value}” ({field}) is not in the #rrggbb format (for example #1f4e79)."
        for field, value in colors
        if value is not None and not _HEX_COLOR.match(value)
    ]


def template_problems(spec: TemplateSpec, available_fonts: Collection[str]) -> list[str]:
    """The defects of a description, as English sentences sent back to the model: column widths
    totalling 100%, each section at most once and "identity" exactly once, fonts taken from
    `available_fonts` (case ignored), #rrggbb colours."""
    return [
        *_layout_problems(spec),
        *_font_problems(spec, available_fonts),
        *_color_problems(spec),
    ]
