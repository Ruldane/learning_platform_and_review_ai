"""Tightening the template when the generated CV has more pages than the original (SPEC 5.3,
step 9; D120): three levels, applied one after the other (each starts from the spec of the
previous level), with a new render after each. Never the margins or the colors; a value never
increases.

The second argument is the floor of the body text (preflight G20): `MIN_BODY_PT` if the
original's `font_sizes` check passed, otherwise 8."""

from collections.abc import Callable

from app.agents.tools.template_schema import TemplateSpec

GAP_FACTOR = 0.6
LINE_HEIGHT_STEP = 0.1
MIN_LINE_HEIGHT = 1.1
BODY_STEP_PT = 0.5
LOOSE_MIN_BODY_PT = 8.0

TightenStep = Callable[[TemplateSpec, float], TemplateSpec]


def _fonts(spec: TemplateSpec, **changes: float) -> TemplateSpec:
    return spec.model_copy(update={"fonts": spec.fonts.model_copy(update=changes)})


def tighten_gap(spec: TemplateSpec, min_body_pt: float) -> TemplateSpec:
    """Level 1: space between blocks × 0.6."""
    return spec.model_copy(update={"gap_mm": round(spec.gap_mm * GAP_FACTOR, 2)})


def tighten_line_height(spec: TemplateSpec, min_body_pt: float) -> TemplateSpec:
    """Level 2: line spacing − 0.1, not below 1.1 (nor above its value)."""
    current = spec.fonts.line_height
    lowered = max(MIN_LINE_HEIGHT, round(current - LINE_HEIGHT_STEP, 2))
    return _fonts(spec, line_height=min(current, lowered))


def tighten_body(spec: TemplateSpec, min_body_pt: float) -> TemplateSpec:
    """Level 3: body text − 0.5 pt, not below `min_body_pt` (nor above its value)."""
    current = spec.fonts.body_pt
    lowered = max(min_body_pt, round(current - BODY_STEP_PT, 2))
    return _fonts(spec, body_pt=min(current, lowered))


TIGHTEN_STEPS: tuple[TightenStep, ...] = (tighten_gap, tighten_line_height, tighten_body)
