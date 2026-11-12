"""Notes d'un quiz (F9) : QCM tout ou rien, ouvertes à 0, 0,5 ou 1, réussite à 80 %."""

import pytest

from app.features.quiz.service.scoring import (
    OPEN_SCORES,
    PASS_PERCENT,
    passed,
    qcm_points,
    score_percent,
    weak_skills,
)


def test_constants() -> None:
    assert PASS_PERCENT == 80 and OPEN_SCORES == (0.0, 0.5, 1.0)


@pytest.mark.parametrize(
    ("correct", "choice", "points"),
    [(2, 2, 1.0), (2, 1, 0.0), (2, None, 0.0), (None, 0, 0.0), (0, 0, 1.0)],
)
def test_qcm_points(correct: int | None, choice: int | None, points: float) -> None:
    assert qcm_points(correct, choice) == points


def test_score_and_pass() -> None:
    assert score_percent([1, 1, 1, 1, 0.5]) == 90
    assert passed(80) and not passed(79)


def test_score_of_nothing_is_zero() -> None:
    assert score_percent([]) == 0


def test_score_rounds_half_up() -> None:
    assert score_percent([1, 0, 0, 0, 0, 0, 0, 0]) == 13  # 12,5 -> 13, pas 12
    assert score_percent([1, 0, 0]) == 33
    assert score_percent([1, 1, 0]) == 67


def test_weak_skills_dedup_and_limit() -> None:
    skills = ["Pandas", "SQL", "pandas ", "Rust", "Go", "SQL"]
    points = [0.5, 1.0, 0.0, 0.0, 0.5, 0.0]
    assert weak_skills(skills, points) == ["Pandas", "Rust", "Go"]
    assert weak_skills(skills, points, limit=2) == ["Pandas", "Rust"]
    assert weak_skills(skills, points, limit=0) == []


def test_weak_skills_keeps_first_spelling_and_skips_full_marks() -> None:
    assert weak_skills(["SQL", "Pandas"], [1.0, 1.0]) == []
    assert weak_skills(["  Pandas ", "PANDAS"], [0.0, 0.0]) == ["Pandas"]
    assert weak_skills(["", "SQL"], [0.0, 0.0]) == ["SQL"]
