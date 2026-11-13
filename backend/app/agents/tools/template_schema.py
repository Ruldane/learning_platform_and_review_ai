"""Ce que le Maquettiste écrit : une description du design d'un CV (`TemplateSpec`), jamais du
HTML ni du CSS, que le code écrit à partir d'elle (D118). Les couleurs, les polices et l'agencement
sont vérifiés par `template_problems`, dont les phrases sont rendues au modèle pour qu'il corrige.
"""

import re
from collections import Counter
from collections.abc import Collection
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.agents.tools.cv_schema import SectionKey

# Le format #rrggbb des couleurs est vérifié par `template_problems` (redemandé, pas refusé).
_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
ColumnBlock = SectionKey | Literal["identity"]
Margin = Annotated[float, Field(ge=0, le=40)]


class PageSpec(BaseModel):
    width_pt: float = Field(ge=200, le=1000)
    height_pt: float = Field(ge=200, le=1400)
    margins_mm: tuple[Margin, Margin, Margin, Margin]  # haut, droite, bas, gauche


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
    """Une police d'un gabarit (`cv_templates.fonts`) : `family` est la police libre employée,
    `substitute` dit qu'elle remplace celle du PDF d'origine (preflight G25)."""

    role: Literal["body", "heading"]
    family: str = Field(min_length=1, max_length=60)
    substitute: bool


def _layout_problems(spec: TemplateSpec) -> list[str]:
    problems: list[str] = []
    total = sum(column.width_pct for column in spec.columns)
    if total != 100:
        problems.append(
            f"Les largeurs des colonnes font {total} % au total : elles doivent faire 100 %."
        )
    counts = Counter(block for column in spec.columns for block in column.sections)
    if counts["identity"] != 1:
        problems.append(
            f"Le bloc « identity » doit figurer exactement une fois (il figure "
            f"{counts['identity']} fois)."
        )
    for block, count in counts.items():
        if block != "identity" and count > 1:
            problems.append(
                f"La section « {block} » figure {count} fois : place-la une seule fois, "
                "dans une seule colonne."
            )
    return problems


def _font_problems(spec: TemplateSpec, available_fonts: Collection[str]) -> list[str]:
    known = {font.casefold() for font in available_fonts}
    choices = ", ".join(sorted(available_fonts))
    return [
        f"La police « {family} » n'est pas disponible : choisis parmi {choices}."
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
        colors.append((f"colonne {rank}, background", column.background))
        colors.append((f"colonne {rank}, text_color", column.text_color))
    return [
        f"La couleur « {value} » ({field}) n'est pas au format #rrggbb (par exemple #1f4e79)."
        for field, value in colors
        if value is not None and not _HEX_COLOR.match(value)
    ]


def template_problems(spec: TemplateSpec, available_fonts: Collection[str]) -> list[str]:
    """Les défauts d'une description, en phrases françaises rendues au modèle : largeurs des
    colonnes à 100 % au total, chaque section au plus une fois et « identity » exactement une
    fois, polices prises dans `available_fonts` (casse ignorée), couleurs #rrggbb."""
    return [
        *_layout_problems(spec),
        *_font_problems(spec, available_fonts),
        *_color_problems(spec),
    ]
