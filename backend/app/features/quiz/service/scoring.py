"""Quiz scores (SPEC F9, D99): pure rules. A multiple-choice question is worth 0 or 1 point, an
open question 0, 0.5 or 1 according to the grid; 80% or more makes the skill `valide`."""

from collections.abc import Sequence
from math import floor

from app.core.skills import normalize_skill_name

PASS_PERCENT = 80
OPEN_SCORES = (0.0, 0.5, 1.0)


def qcm_points(correct_index: int | None, choice: int | None) -> float:
    """1 point if January chose the right answer, otherwise 0 (no answer included)."""
    return 1.0 if correct_index is not None and choice == correct_index else 0.0


def score_percent(points: Sequence[float]) -> int:
    """The score as a whole percentage, rounded to the nearest integer (12.5 gives 13); no question:
    0."""
    if not points:
        return 0
    return floor(100 * sum(points) / len(points) + 0.5)


def passed(score: int) -> bool:
    return score >= PASS_PERCENT


def weak_skills(skills: Sequence[str], points: Sequence[float], limit: int = 3) -> list[str]:
    """The skills of the questions worth under 1 point, in order of appearance, without duplicates
    (normalized name; the first spelling is kept), `limit` at most."""
    weak: dict[str, str] = {}
    for name, point in zip(skills, points, strict=True):
        norm = normalize_skill_name(name)
        if point < 1 and norm and norm not in weak:
            weak[norm] = name.strip()
    return list(weak.values())[: max(0, limit)]
