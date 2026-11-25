"""Score de match et compétences les plus manquantes (6.2, F8)."""

import math
from fractions import Fraction
from itertools import combinations_with_replacement

from app.db.models.skills import SkillLevel
from app.features.gap.service.score import (
    GapAction,
    GapRow,
    GapSource,
    MissingSkill,
    match_score,
    top_missing,
)


def row(
    required: bool, level: SkillLevel | None, skill: str = "Python", source: GapSource = "posting"
) -> GapRow:
    action: GapAction = "to_add" if level is None else "in_program"
    return GapRow(skill, required, level, action, None, source)


def test_match_score_weights() -> None:
    assert match_score([row(True, "validated"), row(False, None)]) == 67


def test_match_score_levels() -> None:
    assert match_score([row(True, "declared")]) == 60
    assert match_score([row(False, "in_progress")]) == 30
    assert match_score([row(True, "proven"), row(True, "in_progress")]) == 65
    assert match_score([row(False, "validated"), row(False, None)]) == 50


def test_match_score_rounds_half_up_exactly() -> None:
    # 100 × (2 × 1 + 1 × 0,3 + 1 × 0) / 4 = 57,5 → 58 (en flottant : 57,499… → 57).
    assert match_score([row(True, "validated"), row(False, "in_progress"), row(False, None)]) == 58


def test_match_score_matches_exact_fractions() -> None:
    levels: list[SkillLevel | None] = ["validated", "declared", "in_progress", None]
    exact: dict[SkillLevel | None, Fraction] = {
        "validated": Fraction(1),
        "declared": Fraction(6, 10),
        "in_progress": Fraction(3, 10),
        None: Fraction(0),
    }
    choices = [(required, level) for required in (True, False) for level in levels]
    for size in range(1, 6):
        for combo in combinations_with_replacement(choices, size):
            rows = [row(required, level) for required, level in combo]
            weight = sum(2 if required else 1 for required, _ in combo)
            earned = sum((2 if r else 1) * exact[level] for r, level in combo)
            expected = math.floor(100 * Fraction(earned) / weight + Fraction(1, 2))
            assert match_score(rows) == expected, combo


def test_match_score_without_rows_is_zero() -> None:
    assert match_score([]) == 0


def test_cv_review_rows_do_not_change_the_score() -> None:
    rows = [row(True, "validated"), row(False, None, "AWS", "cv_review")]
    assert match_score(rows) == 100
    assert match_score([row(True, None, "AWS", "cv_review")]) == 0


def test_top_missing_counts_once_per_posting_and_limits() -> None:
    gaps = [
        # « Docker » deux fois dans la même offre, dont une obligatoire : une offre, obligatoire.
        [row(False, None, "Docker"), row(True, None, "docker"), row(True, "declared", "SQL")],
        [row(False, None, "Docker"), row(True, None, "Kubernetes"), row(False, None, "AWS")],
        [row(True, None, "Kubernetes"), row(True, "validated", "Docker")],
    ]
    assert top_missing(gaps) == [
        MissingSkill("Docker", 2, 1),
        MissingSkill("Kubernetes", 2, 2),
        MissingSkill("AWS", 1, 0),
    ]
    assert top_missing(gaps, limit=1) == [MissingSkill("Docker", 2, 1)]


def test_top_missing_keeps_ten_and_skips_declared() -> None:
    gaps = [
        [row(False, None, f"Outil {n:02d}") for n in range(15)] + [row(True, "declared", "SQL")]
    ]
    top = top_missing(gaps)
    assert len(top) == 10 and top[0] == MissingSkill("Outil 00", 1, 0)
    assert all(missing.skill != "SQL" for missing in top)
    assert top_missing([]) == []
