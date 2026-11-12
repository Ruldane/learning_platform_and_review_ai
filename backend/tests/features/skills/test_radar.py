"""Radar par domaine (F15) : moyenne des niveaux (0, 25, 50, 75, 100)."""

from app.features.skills.radar import LEVEL_SCORE, domain_scores, level_counts


def test_level_scores() -> None:
    assert LEVEL_SCORE == {None: 0, "declare": 25, "en_cours": 50, "valide": 75, "prouve": 100}


def test_domain_scores() -> None:
    rows = [
        ("Données", "valide"),
        ("Données", "declare"),
        ("Données", None),
        ("Code", "prouve"),
        (None, "en_cours"),
        ("  ", "en_cours"),
    ]
    assert domain_scores(rows) == [("Autres", 50), ("Code", 100), ("Données", 33)]


def test_domain_scores_rounds_half_up_and_handles_empty() -> None:
    rows = [("A", "valide"), ("A", "prouve"), ("A", "declare"), ("A", "declare")]
    assert domain_scores(rows) == [("A", 56)]  # 225 / 4 = 56,25
    assert domain_scores([("A", "declare"), ("A", "en_cours")]) == [("A", 38)]  # 37,5 -> 38
    assert domain_scores([]) == []


def test_level_counts_has_every_level() -> None:
    assert level_counts(["valide", "valide", "declare"]) == {
        "declare": 1,
        "en_cours": 0,
        "valide": 2,
        "prouve": 0,
    }
    assert level_counts([]) == {"declare": 0, "en_cours": 0, "valide": 0, "prouve": 0}
