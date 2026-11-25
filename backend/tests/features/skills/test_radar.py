"""Radar par domaine (F15) : moyenne des niveaux (0, 25, 50, 75, 100)."""

from app.features.skills.radar import LEVEL_SCORE, domain_scores, level_counts


def test_level_scores() -> None:
    assert LEVEL_SCORE == {
        None: 0,
        "declared": 25,
        "in_progress": 50,
        "validated": 75,
        "proven": 100,
    }


def test_domain_scores() -> None:
    rows = [
        ("Données", "validated"),
        ("Données", "declared"),
        ("Données", None),
        ("Code", "proven"),
        (None, "in_progress"),
        ("  ", "in_progress"),
    ]
    assert domain_scores(rows) == [("Code", 100), ("Données", 33), ("Other", 50)]


def test_domain_scores_rounds_half_up_and_handles_empty() -> None:
    rows = [("A", "validated"), ("A", "proven"), ("A", "declared"), ("A", "declared")]
    assert domain_scores(rows) == [("A", 56)]  # 225 / 4 = 56,25
    assert domain_scores([("A", "declared"), ("A", "in_progress")]) == [("A", 38)]  # 37,5 -> 38
    assert domain_scores([]) == []


def test_level_counts_has_every_level() -> None:
    assert level_counts(["validated", "validated", "declared"]) == {
        "declared": 1,
        "in_progress": 0,
        "validated": 2,
        "proven": 0,
    }
    assert level_counts([]) == {"declared": 0, "in_progress": 0, "validated": 0, "proven": 0}


def test_french_other_domain_is_merged_with_other() -> None:
    """Skills stored with the French label before the switch to English join "Other"."""
    rows = [("Autres", "validated"), (None, "declared")]
    assert domain_scores(rows) == [("Other", 50)]
