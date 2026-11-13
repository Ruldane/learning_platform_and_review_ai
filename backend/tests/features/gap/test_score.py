"""Score de match et compétences les plus manquantes (6.2, F8)."""

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
    assert match_score([row(True, "valide"), row(False, None)]) == 67


def test_match_score_levels() -> None:
    assert match_score([row(True, "declare")]) == 60
    assert match_score([row(False, "en_cours")]) == 30
    assert match_score([row(True, "prouve"), row(True, "en_cours")]) == 65
    assert match_score([row(False, "valide"), row(False, None)]) == 50


def test_match_score_without_rows_is_zero() -> None:
    assert match_score([]) == 0


def test_cv_review_rows_do_not_change_the_score() -> None:
    rows = [row(True, "valide"), row(False, None, "AWS", "cv_review")]
    assert match_score(rows) == 100
    assert match_score([row(True, None, "AWS", "cv_review")]) == 0


def test_top_missing_counts_once_per_posting_and_limits() -> None:
    gaps = [
        # « Docker » deux fois dans la même offre, dont une obligatoire : une offre, obligatoire.
        [row(False, None, "Docker"), row(True, None, "docker"), row(True, "declare", "SQL")],
        [row(False, None, "Docker"), row(True, None, "Kubernetes"), row(False, None, "AWS")],
        [row(True, None, "Kubernetes"), row(True, "valide", "Docker")],
    ]
    assert top_missing(gaps) == [
        MissingSkill("Docker", 2, 1),
        MissingSkill("Kubernetes", 2, 2),
        MissingSkill("AWS", 1, 0),
    ]
    assert top_missing(gaps, limit=1) == [MissingSkill("Docker", 2, 1)]


def test_top_missing_keeps_ten_and_skips_declared() -> None:
    gaps = [[row(False, None, f"Outil {n:02d}") for n in range(15)] + [row(True, "declare", "SQL")]]
    top = top_missing(gaps)
    assert len(top) == 10 and top[0] == MissingSkill("Outil 00", 1, 0)
    assert all(missing.skill != "SQL" for missing in top)
    assert top_missing([]) == []
