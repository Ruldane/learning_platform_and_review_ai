"""Resserrement du gabarit quand le CV généré a plus de pages que l'original (SPEC 5.3, étape 9 ;
D120) : trois paliers, à appliquer l'un après l'autre (chacun part du spec du palier précédent),
avec un nouveau rendu après chacun. Jamais les marges ni les couleurs ; une valeur n'augmente
jamais.

Le second argument est le plancher du corps de texte (preflight G20) : `MIN_BODY_PT` si le
contrôle `font_sizes` de l'original était réussi, sinon 8."""

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
    """Palier 1 : espace entre les blocs × 0,6."""
    return spec.model_copy(update={"gap_mm": round(spec.gap_mm * GAP_FACTOR, 2)})


def tighten_line_height(spec: TemplateSpec, min_body_pt: float) -> TemplateSpec:
    """Palier 2 : interligne − 0,1, pas sous 1,1 (ni au-dessus de sa valeur)."""
    current = spec.fonts.line_height
    lowered = max(MIN_LINE_HEIGHT, round(current - LINE_HEIGHT_STEP, 2))
    return _fonts(spec, line_height=min(current, lowered))


def tighten_body(spec: TemplateSpec, min_body_pt: float) -> TemplateSpec:
    """Palier 3 : corps du texte − 0,5 pt, pas sous `min_body_pt` (ni au-dessus de sa valeur)."""
    current = spec.fonts.body_pt
    lowered = max(min_body_pt, round(current - BODY_STEP_PT, 2))
    return _fonts(spec, body_pt=min(current, lowered))


TIGHTEN_STEPS: tuple[TightenStep, ...] = (tighten_gap, tighten_line_height, tighten_body)
