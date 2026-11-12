"""Bilan hebdomadaire (F13) : retard, état, options, texte."""

from dataclasses import replace
from datetime import date

import pytest

from app.agents.tools.study_schema import ReviewState
from app.features.replan.service.review import (
    LATE_THRESHOLD,
    WeekFacts,
    classify,
    late_ratio,
    options_for,
    review_text,
)

FACTS = WeekFacts(
    week_start=date(2026, 11, 9),
    planned_minutes=390,
    done_minutes=195,
    tasks_planned=9,
    tasks_done=4,
    late_minutes=0,
    quiz_scores=[85],
    done_ahead=0,
    study_minutes=130,
    captures=3,
)


def test_late_ratio() -> None:
    assert LATE_THRESHOLD == 0.30
    assert late_ratio(replace(FACTS, planned_minutes=200, late_minutes=50)) == 0.25
    assert late_ratio(replace(FACTS, planned_minutes=0, late_minutes=50)) == 0.0


@pytest.mark.parametrize(
    ("ratio", "previous", "state"),
    [
        (0.5, 0.4, "late_twice"),
        (0.5, 0.2, "late"),
        (0.5, None, "late"),
        (0.3, 0.9, "late"),  # 30 % pile n'est pas « plus de 30 % »
        (0.35, 0.3, "late"),
        (0.1, 0.9, "late"),
        (0.0, None, "on_track"),
        (0.0, 0.9, "on_track"),
    ],
)
def test_classify(ratio: float, previous: float | None, state: ReviewState) -> None:
    facts = replace(FACTS, planned_minutes=1000, late_minutes=round(ratio * 1000))
    assert classify(facts, previous) == state


def test_ahead_when_week_done_and_next_week_started() -> None:
    assert classify(replace(FACTS, done_ahead=2), None) == "ahead"
    assert classify(replace(FACTS, done_ahead=1), 0.5) == "ahead"
    # un retard prime sur l'avance
    assert classify(replace(FACTS, done_ahead=2, late_minutes=30), None) == "late"
    assert classify(replace(FACTS, done_ahead=0), None) == "on_track"


def test_options_for() -> None:
    assert options_for("late_twice") == ("reduce_scope", "push_deadline")
    assert options_for("ahead") == ("advance", "deepen")
    assert options_for("late") == ()
    assert options_for("on_track") == ()


def test_review_text() -> None:
    assert review_text(FACTS) == (
        "Semaine du 09/11 : 6 h 30 prévues, 3 h 15 faites, 4 tâches sur 9, quiz 85 %, "
        "2 h 10 d'étude, 3 captures."
    )


def test_review_text_edge_cases() -> None:
    text = review_text(
        replace(
            FACTS,
            planned_minutes=120,
            done_minutes=45,
            tasks_planned=2,
            tasks_done=1,
            quiz_scores=[],
            study_minutes=0,
            captures=1,
        )
    )
    assert text == (
        "Semaine du 09/11 : 2 h prévues, 45 min faites, 1 tâche sur 2, aucun quiz, "
        "0 min d'étude, 1 capture."
    )
    assert "quiz 80 %" in review_text(replace(FACTS, quiz_scores=[90, 70]))
    assert "2 h 05 d'étude" in review_text(replace(FACTS, study_minutes=125))
