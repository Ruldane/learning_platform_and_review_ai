"""Description d'un gabarit (6.2) : défauts rendus au Maquettiste en phrases françaises."""

from typing import Any

import pytest
from pydantic import ValidationError

from app.agents.tools.template_schema import ColumnSpec, FontUse, TemplateSpec, template_problems

FONTS = {"Lato", "Carlito"}


def spec(**kwargs: Any) -> TemplateSpec:
    fields: dict[str, Any] = {
        "page": {"width_pt": 595.0, "height_pt": 842.0, "margins_mm": (15, 12, 15, 12)},
        "columns": [
            {
                "width_pct": 30,
                "background": "#1f4e79",
                "text_color": "#ffffff",
                "sections": ["identity", "skills", "languages", "links"],
            },
            {"width_pct": 70, "sections": ["summary", "experience", "education"]},
        ],
        "fonts": {
            "body": "Lato",
            "heading": "carlito",
            "body_pt": 10,
            "heading_pt": 13,
            "name_pt": 22,
            "line_height": 1.25,
        },
        "accent": "#1F4E79",
        "text": "#222222",
        "muted": "#666666",
        "section_title": "underline",
        "uppercase_titles": True,
        "dates": "right",
        "bullets": "dot",
        "gap_mm": 4,
    }
    return TemplateSpec.model_validate(fields | kwargs)


def _columns(*columns: tuple[int, list[str]]) -> list[ColumnSpec]:
    return [ColumnSpec.model_validate({"width_pct": w, "sections": s}) for w, s in columns]


specs = {
    "widths_99": spec(columns=_columns((30, ["identity"]), (69, ["experience"]))),
    "section_twice": spec(columns=_columns((40, ["identity", "skills"]), (60, ["skills"]))),
    "unknown_font": spec(
        fonts={
            "body": "Garamond",
            "heading": "Lato",
            "body_pt": 10,
            "heading_pt": 12,
            "name_pt": 20,
            "line_height": 1.2,
        }
    ),
    "color_rgb_name": spec(accent="red", header_band="rgb(0, 0, 0)"),
    "no_identity": spec(columns=_columns((100, ["summary", "experience"]))),
}


def test_valid_spec_has_no_problem() -> None:
    assert template_problems(spec(), FONTS) == []


@pytest.mark.parametrize(
    "bad", ["widths_99", "section_twice", "unknown_font", "color_rgb_name", "no_identity"]
)
def test_template_problems(bad: str) -> None:
    assert template_problems(specs[bad], FONTS)


def test_problems_are_french_sentences() -> None:
    assert template_problems(specs["widths_99"], FONTS) == [
        "Les largeurs des colonnes font 99 % au total : elles doivent faire 100 %."
    ]
    assert template_problems(specs["unknown_font"], FONTS) == [
        "La police « Garamond » n'est pas disponible : choisis parmi Carlito, Lato."
    ]
    assert len(template_problems(specs["color_rgb_name"], FONTS)) == 2
    assert "« skills » figure 2 fois" in template_problems(specs["section_twice"], FONTS)[0]
    assert "« identity »" in template_problems(specs["no_identity"], FONTS)[0]


@pytest.mark.parametrize(
    "bad",
    [
        {"page": {"width_pt": 595, "height_pt": 842, "margins_mm": (15, 15, 15, 41)}},
        {"page": {"width_pt": 100, "height_pt": 842, "margins_mm": (15, 15, 15, 15)}},
        {"columns": []},
        {"gap_mm": 21},
    ],
)
def test_spec_bounds(bad: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        spec(**bad)


def test_font_use() -> None:
    use = FontUse(role="body", family="Carlito", substitute=True)
    assert use.model_dump() == {"role": "body", "family": "Carlito", "substitute": True}
