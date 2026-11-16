"""Règles pures des projets : forme du rendu, verdict, début de semaine (8.1, P1 à P3)."""

from datetime import date
from typing import Any

from app.features.projects.service.rules import (
    DESCRIPTION_MAX,
    IMAGE_TYPES,
    SCREENSHOT_BYTES,
    SCREENSHOTS_MAX,
    submission_problems,
    verdict,
    week_started,
)


def test_constants() -> None:
    assert (DESCRIPTION_MAX, SCREENSHOTS_MAX, SCREENSHOT_BYTES) == (4000, 5, 5 * 1024 * 1024)
    assert IMAGE_TYPES == {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}


def test_submission_needs_link_or_description() -> None:
    assert submission_problems(None, "  ", 3) == ["repo_url", "description"]
    assert submission_problems("", None, 0) == ["repo_url", "description"]
    assert submission_problems(" ", "", 0) == ["repo_url", "description"]


def test_submission_accepts_a_link_or_a_description_alone() -> None:
    assert submission_problems("https://github.com/moi/projet", None, 0) == []
    assert submission_problems(None, "J'ai fait un tableau de bord.", 5) == []
    assert submission_problems("http://exemple.fr/depot", "Texte", 2) == []


def test_submission_link_must_be_http() -> None:
    assert submission_problems("ftp://exemple.fr/depot", "Texte", 0) == ["repo_url"]
    assert submission_problems("javascript:alert(1)", None, 0) == ["repo_url"]
    assert submission_problems("github.com/moi/projet", None, 0) == ["repo_url"]
    assert submission_problems("https://", None, 0) == ["repo_url"]
    assert submission_problems("https://exemple.fr/un depot", None, 0) == ["repo_url"]


def test_submission_screenshot_and_description_limits() -> None:
    assert submission_problems(None, "Texte", SCREENSHOTS_MAX) == []
    assert submission_problems(None, "Texte", SCREENSHOTS_MAX + 1) == ["screenshots"]
    assert submission_problems(None, "x" * DESCRIPTION_MAX, 0) == []
    assert submission_problems(None, "x" * (DESCRIPTION_MAX + 1), 0) == ["description"]
    assert submission_problems("ftp://x", "x" * (DESCRIPTION_MAX + 1), 6) == [
        "repo_url",
        "description",
        "screenshots",
    ]


def res(index: int, met: bool = True) -> dict[str, Any]:
    return {"index": index, "met": met, "comment": "ok"}


def test_verdict_all_met() -> None:
    assert verdict(3, [res(1), res(2), res(3)]) == "validated"
    assert verdict(3, [res(3), res(1), res(2)]) == "validated"  # l'ordre importe peu


def test_verdict_one_unmet_criterion() -> None:
    assert verdict(3, [res(1), res(2, False), res(3)]) == "to_redo"


def test_verdict_needs_every_criterion() -> None:
    assert verdict(4, [res(1), res(2), res(3)]) == "to_redo"  # un critère manque
    assert verdict(3, [res(1), res(2), res(2)]) == "to_redo"  # un index en double
    assert verdict(3, [res(1), res(2), res(3), res(3)]) == "to_redo"
    assert verdict(2, [res(1), res(2), res(3)]) == "to_redo"  # hors bornes
    assert verdict(2, [res(0), res(1)]) == "to_redo"
    assert verdict(2, [res(1), {"met": True}]) == "to_redo"  # sans index


def test_verdict_never_validates_nothing() -> None:
    assert verdict(0, []) == "to_redo"
    assert verdict(3, []) == "to_redo"
    assert verdict(1, [{"index": 1, "met": "yes"}]) == "to_redo"  # « atteint » est un booléen


def test_week_started() -> None:
    monday = date(2026, 11, 16)
    assert not week_started(monday, date(2026, 11, 15))
    assert week_started(monday, monday)
    assert week_started(monday, date(2026, 12, 1))


def test_submission_link_is_capped_at_2048_characters() -> None:
    long_link = "https://exemple.fr/" + "a" * 2029  # 2 048 caractères : accepté
    assert len(long_link) == 2048 and submission_problems(long_link, None, 0) == []
    assert submission_problems(long_link + "a", None, 0) == ["repo_url"]
