"""Détection d'une question salariale (7.1) : la réponse reste vide, imposée par le code."""

import pytest

from app.agents.tools.salary import is_salary_question


@pytest.mark.parametrize(
    "q",
    [
        "Quelles sont vos prétentions salariales ?",
        "Expected salary",
        "Votre TJM ?",
        "Rémunération souhaitée",
        "REMUNERATION ACTUELLE",
        "Quel est votre package actuel ?",
        "What are your compensation expectations?",
        "What is your expected pay?",
        "Desired pay range",
        "Fourchette de salaire attendue",
        "Taux journalier moyen (TJM) ?",
        "Quelle est votre prétention ?",
    ],
)
def test_salary_questions_detected(q: str) -> None:
    assert is_salary_question(q)


@pytest.mark.parametrize(
    "q",
    [
        "Êtes-vous disponible sous 3 mois ?",
        "Pourquoi cette entreprise ?",
        "Quels langages maîtrisez-vous ?",
        "Do you need visa sponsorship?",
        "Please pay attention to the deadline",
        "",
    ],
)
def test_non_salary_question(q: str) -> None:
    assert not is_salary_question(q)
