"""Règles de la partie « revue » du contrôle de la phase 6 : chacune échoue sans recopier un texte
du CV ni de l'offre."""

from typing import Any

import pytest

from scripts.phase4_rules import CheckFailed
from scripts.phase6_review_rules import (
    ATS_CHECKS,
    FILENAME_PREFIX,
    check_bulk,
    check_decided,
    check_proposals,
    check_version,
    foreign_terms,
    has_term,
    pick_refusal,
    profile_text,
)
from scripts.sample_cv import make_cv_pdf


def mod(ref: str, status: str = "proposed", **over: Any) -> dict[str, Any]:
    base = {
        "id": f"id-{ref}", "ref": ref, "status": status, "action": "rewrite",
        "after": "Texte sans rien de spécial", "fact_ids": ["x1a1"],
    }  # fmt: skip
    return base | over


def review(*mods: dict[str, Any], gap: list[str] | None = None) -> dict[str, Any]:
    return {
        "modifications": list(mods),
        "gap_terms": gap or [],
        "before": {"coverage_percent": 40},
    }


PROFILE = "Python, Docker et des agents conversationnels"
THREE = (mod("a1"), mod("a2", "to_confirm"), mod("r1"))


def test_proposals_count_the_held_ones_and_the_gap_terms() -> None:
    assert check_proposals("revue", review(*THREE, gap=["RAG"]), PROFILE) == (1, 1, 1)


def test_a_gap_term_written_by_the_profile_is_not_foreign() -> None:
    gap = review(*THREE, gap=["agents", "RAG"])
    assert foreign_terms(gap, "Livré des agents conversationnels") == ["RAG"]
    assert profile_text({"a": "Python", "b": [{"name": "Docker"}, {"n": 3}]}).split() == [
        "Python",
        "Docker",
    ]


def test_proposals_need_three_modifications_and_cited_facts() -> None:
    with pytest.raises(CheckFailed, match="2 modification"):
        check_proposals("revue", review(mod("a1"), mod("a2")), PROFILE)
    with pytest.raises(CheckFailed, match="sans fait cité : a1"):
        check_proposals("revue", review(mod("a1", fact_ids=[]), mod("a2"), mod("a3")), PROFILE)


def test_proposals_refuse_a_gap_term_in_a_kept_text_but_not_a_refused_one() -> None:
    leaky = mod("a1", after="Des chaînes RAG évaluées")
    with pytest.raises(CheckFailed, match="écart dans le texte de : a1") as failed:
        check_proposals("revue", review(leaky, mod("a2"), mod("a3"), gap=["RAG"]), PROFILE)
    assert "chaînes" not in str(failed.value)
    refused = mod("a1", "refused", after="Des chaînes RAG évaluées")
    check_proposals("revue", review(refused, mod("a2"), mod("a3"), gap=["RAG"]), PROFILE)


def test_a_term_matches_whole_words_only() -> None:
    assert has_term("Des chaînes RAG évaluées", "rag")
    assert not has_term("Du stockage et du drague", "rag")


def test_bulk_skips_exactly_the_held_ones() -> None:
    mods = list(THREE)
    check_bulk("décisions", mods, {"updated": 2, "skipped": ["id-a2"]})
    with pytest.raises(CheckFailed):
        check_bulk("décisions", mods, {"updated": 3, "skipped": []})
    with pytest.raises(CheckFailed):
        check_bulk("décisions", mods, {"updated": 1, "skipped": ["id-a2"]})


def test_refusal_keeps_one_accepted_modification() -> None:
    assert pick_refusal("décisions", list(THREE))["ref"] == "r1"
    assert pick_refusal("décisions", [mod("a1"), mod("a2", "to_confirm")])["ref"] == "a2"
    with pytest.raises(CheckFailed, match="Aucune modification acceptable"):
        pick_refusal("décisions", [mod("a1", "to_confirm")])


def test_decided_checks_statuses_after_the_clicks() -> None:
    before = list(THREE)
    after = review(mod("a1", "accepted"), mod("a2", "to_confirm"), mod("r1", "refused"))
    check_decided("décisions", after, before, "id-r1", PROFILE)
    with pytest.raises(CheckFailed, match="a1"):
        check_decided("décisions", after, before, "id-a1", PROFILE)


CHECKS = [{"id": name, "passed": True, "detail": ""} for name in ATS_CHECKS]


def version(**over: Any) -> dict[str, Any]:
    checks = CHECKS
    base = {
        "id": "v1", "number": 1, "filename": f"{FILENAME_PREFIX}AI_Product_Engineer.pdf",
        "page_count": 1, "original_page_count": 1, "decisions": {"a1": "accepted"},
        "indicators": {"coverage_percent": 60, "checks": checks},
    }  # fmt: skip
    return base | over


def test_version_passes_on_the_sample_pdf() -> None:
    header = f'attachment; filename="{FILENAME_PREFIX}AI_Product_Engineer.pdf"'
    one = review(mod("a1", "accepted"))
    assert check_version("génération", version(), one, make_cv_pdf(), header, PROFILE) == 0


@pytest.mark.parametrize(
    ("over", "message"),
    [
        ({"filename": "CV_Autre.pdf"}, "Nom de fichier"),
        ({"page_count": 2}, r"page\(s\)"),
        ({"decisions": {"a1": "refused"}}, "Décision de a1"),
        ({"indicators": {"coverage_percent": 10, "checks": CHECKS}}, "Couverture"),
        ({"indicators": {"coverage_percent": 60, "checks": []}}, "Contrôles ATS"),
    ],
)  # fmt: skip
def test_version_fails_on_each_broken_rule(over: dict[str, Any], message: str) -> None:
    header = f'attachment; filename="{FILENAME_PREFIX}AI_Product_Engineer.pdf"'
    one = review(mod("a1", "accepted"))
    with pytest.raises(CheckFailed, match=message):
        check_version("génération", version(**over), one, make_cv_pdf(), header, PROFILE)


def test_version_refuses_a_file_that_is_not_a_pdf() -> None:
    header = f'attachment; filename="{FILENAME_PREFIX}AI_Product_Engineer.pdf"'
    one = review(mod("a1", "accepted"))
    with pytest.raises(CheckFailed, match="pas un PDF"):
        check_version("génération", version(), one, b"texte", header, PROFILE)
