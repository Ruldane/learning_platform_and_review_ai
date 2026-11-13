"""Resserrement du gabarit pour garder le nombre de pages de l'original (6.4, SPEC 5.3 étape 9)."""

import pytest

from app.agents.tools.template_schema import FontSpec, TemplateSpec
from app.features.cv.service.ats_checks import MIN_BODY_PT
from app.features.cv.service.tighten import LOOSE_MIN_BODY_PT, TIGHTEN_STEPS
from tests.support.cv_template import spec


def _all_steps(template: TemplateSpec, floor: float) -> TemplateSpec:
    for step in TIGHTEN_STEPS:
        template = step(template, floor)
    return template


def test_three_steps_in_order() -> None:
    original = spec(gap_mm=5)
    gap, line, body = TIGHTEN_STEPS
    first = gap(original, MIN_BODY_PT)
    assert first.gap_mm == 3 and first.fonts == original.fonts
    second = line(first, MIN_BODY_PT)
    assert second.fonts.line_height == pytest.approx(1.2) and second.gap_mm == 3
    third = body(second, 8)
    assert third.fonts.body_pt == 9.5 and third.fonts.line_height == pytest.approx(1.2)


def test_tighten_never_goes_below_min_body() -> None:
    at_floor = _all_steps(spec(), MIN_BODY_PT)  # corps de 10 pt : déjà au plancher
    assert at_floor.fonts.body_pt == MIN_BODY_PT
    loose = spec(fonts=FontSpec(body="Lato", heading="Lato", body_pt=8.2, heading_pt=11,
                                name_pt=20, line_height=1.15))  # fmt: skip
    tightened = _all_steps(loose, LOOSE_MIN_BODY_PT)
    assert tightened.fonts.body_pt == LOOSE_MIN_BODY_PT and tightened.fonts.line_height == 1.1
    # Une valeur déjà sous le plancher n'est jamais relevée.
    small = spec(fonts=loose.fonts.model_copy(update={"body_pt": 7.5, "line_height": 1.05}))
    kept = _all_steps(small, LOOSE_MIN_BODY_PT)
    assert (kept.fonts.body_pt, kept.fonts.line_height) == (7.5, 1.05)


def test_tighten_never_touches_margins_or_colors() -> None:
    original = spec(header_band="#21549a")
    tightened = _all_steps(_all_steps(original, MIN_BODY_PT), MIN_BODY_PT)
    assert tightened.page == original.page and tightened.columns == original.columns
    for name in ("accent", "text", "muted", "header_band", "section_title", "dates", "bullets"):
        assert getattr(tightened, name) == getattr(original, name)
    assert tightened.fonts.heading_pt == original.fonts.heading_pt
    assert original.gap_mm == 4 and original.fonts.line_height == 1.3  # entrée intacte
