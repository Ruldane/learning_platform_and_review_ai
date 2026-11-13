"""Règles du contrôle de fin de phase 5 (étude), en fonctions pures : chacune échoue en nommant
l'étape et un nombre, jamais un texte reçu."""

from datetime import date
from typing import Any

import pytest

from scripts.phase4_rules import CheckFailed
from scripts.phase5_rules import (
    check_attempt,
    check_quiz,
    check_study_summary,
    option_value,
)

DAYS = {date(2026, 11, 19)}


def question(rank: int, type_: str = "short", **over: Any) -> dict[str, Any]:
    choices = ["a", "b", "c"] if type_ == "qcm" else []
    found = {"id": f"q{rank}", "rank": rank, "type": type_, "choices": choices, "code": None}
    return found | over


def quiz(count: int = 10) -> dict[str, Any]:
    types = ("qcm", "short", "code", "explain")
    return {
        "questions": [
            question(n + 1, types[n % 4], **({"code": "x = 1"} if n % 4 == 2 else {}))
            for n in range(count)
        ]
    }


@pytest.mark.parametrize(
    ("found", "message"),
    [
        (quiz(7), "7 question"),
        (quiz(13), "13 question"),
        ({"questions": [question(n) for n in range(1, 11)]}, "1 type"),
        ({"questions": [question(1, "qcm", choices=["a", "b"])] + quiz(9)["questions"]}, "2 choix"),
        ({"questions": [question(1, "short", choices=["a"])] + quiz(9)["questions"]}, "hors QCM"),
        ({"questions": [question(1, "code")] + quiz(9)["questions"]}, "sans code"),
    ],
)
def test_quiz_rules(found: dict[str, Any], message: str) -> None:
    with pytest.raises(CheckFailed, match=message) as caught:
        check_quiz(found)
    assert caught.value.step == "quiz"


def test_a_good_quiz_passes() -> None:
    check_quiz(quiz())


def result(points: float, explanation: str = "Parce que.") -> dict[str, Any]:
    return {"points": points, "explanation": explanation}


def followup(*tasks: str, retry_on: str | None = "2026-11-19", unplaced: int = 0) -> dict[str, Any]:
    return {"revision_tasks": list(tasks), "retry_on": retry_on, "unplaced": unplaced}


def attempt(value: int, results: list[dict[str, Any]], **over: Any) -> dict[str, Any]:
    found = {
        "score": value,
        "passed": value >= 80,
        "results": results,
        "followup": None if value >= 80 else followup("Réviser : x"),
    }
    return found | over


@pytest.mark.parametrize(
    ("found", "message"),
    [
        (attempt(50, [result(1)] * 2, score=None), "Note absente"),
        (attempt(50, [result(1)] * 2, score=101), "Note absente"),
        (attempt(50, [result(1)] * 2, score=True), "Note absente"),
        (attempt(50, [result(1)] * 2, passed=True), "incohérent"),
        (attempt(50, [result(1)]), "1 résultat"),
        (attempt(50, [result(1), result(0.5, " ")]), "sans explication"),
        (attempt(90, [result(1)] * 2, followup=followup("x", retry_on=None)), "révisions"),
        (attempt(50, [result(1)] * 2, followup=None), "aucune révision"),
        (attempt(50, [result(1)] * 2, followup=followup(retry_on=None)), "aucune révision"),
        (attempt(50, [result(1)] * 2, followup=followup("x", retry_on="2026-11-20")), "J[+]2"),
    ],
)
def test_attempt_rules(found: dict[str, Any], message: str) -> None:
    with pytest.raises(CheckFailed, match=message):
        check_attempt(found, 2, DAYS)


def test_attempt_passed_and_failed_both_hold() -> None:
    check_attempt(attempt(90, [result(1)] * 2), 2, DAYS)
    check_attempt(attempt(50, [result(1), result(0)]), 2, DAYS)
    check_attempt(attempt(50, [result(0)] * 2, followup=followup(unplaced=2)), 2, DAYS)


def program(*done: str) -> dict[str, Any]:
    titles = ("Lire 1", "Lire 2", "Pratiquer")
    tasks = [{"title": t, "status": "done" if t in done else "todo"} for t in titles]
    return {"weeks": [{"modules": [{"tasks": tasks}]}]}


def study(**over: Any) -> dict[str, Any]:
    found = {
        "status": "finished",
        "minutes": 30,
        "flashcards_created": 2,
        "tasks_done": ["Lire 1", "Lire 2"],
    }
    return found | over


@pytest.mark.parametrize(
    ("found", "reading", "message"),
    [
        (study(status="interrupted"), set(), "interrupted"),
        (study(status="open"), set(), "pas finie"),
        (study(minutes=0), set(), "0 minute"),
        (study(minutes=31), set(), "31 minute"),
        (study(flashcards_created=0), set(), "Aucune fiche"),
        (study(tasks_done=[]), {"Lire 1"}, "Aucune tâche cochée"),
        (study(tasks_done=["Lire 1", "Pratiquer"]), set(), "pas `done`"),
        (study(tasks_done=["Lire 1"]), {"Lire 1", "Lire 2"}, "non cochée"),
    ],
)
def test_study_summary_rules(found: dict[str, Any], reading: set[str], message: str) -> None:
    with pytest.raises(CheckFailed, match=message) as caught:
        check_study_summary(found, program("Lire 1", "Lire 2"), reading)
    assert caught.value.step == "bilan de session"


def test_a_good_summary_passes_with_or_without_a_block() -> None:
    check_study_summary(study(), program("Lire 1", "Lire 2"), {"Lire 1", "Lire 2"})
    check_study_summary(study(tasks_done=[]), program(), set())  # aucune tâche due : rien à cocher


def test_option_is_read_by_value_and_label_is_checked() -> None:
    stuck = {"options": [{"value": "stuck", "label": "Je bloque (1/3)"}]}

    assert option_value(stuck, "stuck", "Je bloque (1/3)") == "stuck"
    with pytest.raises(CheckFailed, match="mauvais libellé"):
        option_value(stuck, "stuck", "Voir la solution")
    with pytest.raises(CheckFailed, match="absente"):
        option_value(stuck, "skip")
