"""Schémas des projets preuves (P3, P4, D165) : bornes de l'énoncé et des brouillons, verdict
calculé par le code, fait de projet et référence d'honnêteté, texte contrôlé de chaque brouillon."""

import json
from typing import Any

import pytest
from pydantic import ValidationError

from app.agents.tools import project_schema
from app.agents.tools.project_schema import (
    DRAFT_KINDS,
    CriterionResult,
    ProjectBrief,
    ProjectDrafts,
    ProjectEvaluation,
    draft_text,
    linkedin_words,
    project_fact,
    project_reference,
    settled_results,
    unmet_count,
    verdict,
)
from app.agents.tools.text_claims import text_claims
from app.db.models import daily
from tests.agents.graphs.project_support import brief_json, drafts_json
from tests.support.cv_review import profile
from tests.support.projects import sample_brief


def result(index: int, met: bool = True) -> CriterionResult:
    return CriterionResult(index=index, met=met, comment="")


def brief(**over: Any) -> ProjectBrief:
    return ProjectBrief.model_validate_json(brief_json(**over))


def test_draft_kinds_are_the_shared_ones() -> None:
    assert set(DRAFT_KINDS) == {"cv_line", "profile_entry", "linkedin_post", "readme_plan"}
    assert project_schema.DraftKind is daily.DraftKind
    assert project_schema.DraftStatus is daily.DraftStatus


@pytest.mark.parametrize(
    "over",
    [
        {"title": "ab"},
        {"hours": 2},
        {"hours": 7},
        {"constraints": ["une seule"]},
        {"constraints": ["a"] * 6},
        {"criteria": ["a", "b"]},
        {"criteria": ["a"] * 7},
        {"deliverable": "zip"},
    ],
)
def test_brief_bounds_are_refused(over: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        brief(**over)


def test_brief_text_is_shortened_not_refused() -> None:
    long = "Une phrase assez longue pour le contexte. " * 40
    kept = brief(context=long, criteria=["c" * 300, "d", "e"])
    assert len(kept.context) <= 900 and len(kept.criteria[0]) <= 200


def test_evaluation_and_results_bounds() -> None:
    with pytest.raises(ValidationError):
        CriterionResult(index=0, met=True, comment="")
    with pytest.raises(ValidationError):
        ProjectEvaluation(results=[result(1)] * 7, feedback="x")
    assert ProjectEvaluation(results=[], feedback="x " * 1000).feedback  # raccourci, pas refusé


@pytest.mark.parametrize(
    ("results", "expected"),
    [
        ([result(1), result(2), result(3)], "validated"),
        ([result(3), result(1), result(2)], "validated"),  # l'ordre ne compte pas
        ([result(1), result(2, False), result(3)], "to_redo"),
        ([result(1), result(2)], "to_redo"),  # un résultat manque
        ([result(1), result(2), result(2), result(3)], "to_redo"),  # un doublon
        ([result(1), result(2), result(3), result(4)], "to_redo"),  # un rang hors de 1 à 3
        ([result(1), result(2), result(4)], "to_redo"),  # le 3 manque, le 4 sort de l'énoncé
        ([], "to_redo"),
    ],
)
def test_verdict_is_computed_by_the_code(results: list[CriterionResult], expected: str) -> None:
    assert verdict(3, results) == expected


def test_verdict_without_criteria_is_never_validated() -> None:
    assert verdict(0, []) == "to_redo"


def test_settled_results_one_per_criterion() -> None:
    raw = [result(2, False), result(1), result(5), result(2)]  # 2 en double, 5 hors énoncé
    settled = settled_results(3, raw)
    assert [r.index for r in settled] == [1, 2, 3]
    assert [r.met for r in settled] == [True, False, False]
    assert settled[1].comment == project_schema.NOT_ASSESSED == settled[2].comment
    assert unmet_count(3, raw) == 2 and unmet_count(3, [result(i) for i in (1, 2, 3)]) == 0


def test_project_fact_keeps_the_whole_description() -> None:
    words = " ".join(f"mot{n}" for n in range(550))  # ~4 000 caractères
    last = "Résultat final : 42 routes."
    fact = project_fact(
        "Mon projet", f"{words} {last}", ["FastAPI", "FastAPI", " "], "https://x.org"
    )
    assert fact.name == "Mon projet" and fact.link == "https://x.org"
    assert fact.sources == ["january"]
    assert len(fact.description) <= 600 and all(len(a.text) <= 600 for a in fact.achievements)
    text = " ".join([fact.description, *(a.text for a in fact.achievements)])
    assert "mot549" in text and last in text and "Compétences : FastAPI" in text
    assert text.count("FastAPI") == 1


def test_project_fact_without_description_or_skills() -> None:
    fact = project_fact("Titre", None, [], None)
    assert fact.description == "" and fact.achievements == [] and fact.link is None


def test_project_reference_adds_the_fact_and_the_module_skills() -> None:
    validated = profile(skills=["Python"])
    fact = project_fact("API de lecture", "J'ai écrit 3 routes avec FastAPI.", ["Pydantic"], None)
    reference = project_reference(validated, fact, ["Pydantic"])
    assert [p.name for p in reference.projects] == ["API de lecture"] and reference.projects[0].id
    assert {s.name for s in reference.skills} == {"Python", "Pydantic"}
    assert validated.projects == [] and len(validated.skills) == 1  # le profil validé est intact
    assert text_claims("J'ai écrit 3 routes avec FastAPI et Pydantic.", reference) == []
    unsaid = text_claims("Déployé sur Kubernetes pour 10 000 utilisateurs", reference)
    assert {c.term for c in unsaid} == {"10000", "Kubernetes"}


def test_project_reference_without_a_profile() -> None:
    fact = project_fact("Titre du projet", "Une API en Python.", [], None)
    reference = project_reference(None, fact, ["Python"])
    assert reference.identity.name and len(reference.projects) == 1
    assert text_claims("Une API en Python.", reference) == []


def test_draft_text_of_each_kind() -> None:
    drafts = ProjectDrafts.model_validate_json(drafts_json())
    assert draft_text("cv_line", drafts) == drafts.cv_line
    assert draft_text("linkedin_post", drafts) == drafts.linkedin_post
    assert draft_text("readme_plan", drafts) == "\n".join(drafts.readme_plan)
    entry = draft_text("profile_entry", drafts)
    assert entry.splitlines()[0] == drafts.profile_entry.name
    assert drafts.profile_entry.achievements[0] in entry


def test_clean_post_has_80_to_200_words() -> None:
    drafts = ProjectDrafts.model_validate_json(drafts_json())
    assert 80 <= linkedin_words(drafts.linkedin_post) <= 200


@pytest.mark.parametrize(
    "over",
    [
        {"readme_plan": ["a"] * 4},
        {"readme_plan": ["a"] * 11},
        {"cv_line": ""},
        {"profile_entry": {"name": "", "description": "", "achievements": []}},
        {"profile_entry": {"name": "x", "description": "", "achievements": ["a"] * 5}},
    ],
)
def test_drafts_bounds_are_refused(over: dict[str, Any]) -> None:
    data = json.loads(drafts_json()) | over
    with pytest.raises(ValidationError):
        ProjectDrafts.model_validate(data)


def test_sample_brief_is_valid() -> None:
    assert len(sample_brief().criteria) == 4
