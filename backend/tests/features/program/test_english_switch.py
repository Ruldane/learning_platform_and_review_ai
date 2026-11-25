"""Programs stored before the switch to English keep working: French prefixes still match."""

import pytest

from app.agents.tools.plan_schema import TaskDraft
from app.features.program.service.planning import REVIEW_CRITERION, REVIEW_PREFIX, is_review
from app.features.program.service.rules import (
    RETRY_PREFIX,
    is_retry,
    strip_suite_prefix,
    strip_suite_suffix,
    suite_text,
    suite_theme,
)
from app.features.program.service.verbs import review_subject


def _review(title: str, criterion: str) -> TaskDraft:
    return TaskDraft(title=title, type="read", minutes=20, done_criterion=criterion)


def test_is_review_accepts_the_english_and_the_french_review_task() -> None:
    assert is_review(_review(f"{REVIEW_PREFIX}Python", REVIEW_CRITERION))
    legacy = _review(
        "Réviser : Python", "Relire la fiche et répondre aux questions d'auto-évaluation"
    )
    assert is_review(legacy)
    assert not is_review(_review("Review: Python", "Something else"))


@pytest.mark.parametrize("title", [f"{RETRY_PREFIX}Bases", "Refaire le quiz : Bases"])
def test_is_retry_accepts_both_prefixes(title: str) -> None:
    assert is_retry(title, "quiz") and not is_retry(title, "read")


def test_continued_prefix_and_suffix_round_trip() -> None:
    assert suite_theme("Suite : Gros") == "Continued: Gros"
    assert suite_theme("Continued: Gros") == "Continued: Gros"
    assert suite_text("Un dépôt (suite)") == "Un dépôt (continued)"
    assert strip_suite_prefix("Suite : A") == strip_suite_prefix("Continued: A") == "A"
    assert strip_suite_suffix("A (suite)") == strip_suite_suffix("A (continued)") == "A"


@pytest.mark.parametrize("title", ["Review Python", "Review: Python", "Review of Python"])
def test_review_subject_strips_the_english_prefix(title: str) -> None:
    assert review_subject(title) == "Python"
