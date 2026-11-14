"""Règles du contrôle de la phase 6 (`phase6_rules`), sur des réponses fabriquées : aucune
application, aucun réseau. Les messages d'échec ne recopient jamais une valeur du profil."""

from typing import Any

import pytest

from scripts.phase4_rules import CheckFailed
from scripts.phase6_rules import (
    POSTING_SENTENCES,
    check_logs,
    check_profile_facts,
    keywords_in_text,
    skills_below_declared,
)
from tests.support.profile import profile_data


def test_profile_of_the_sample_cv_passes() -> None:
    check_profile_facts("profil", profile_data())


def test_fact_outside_the_cv_is_named_by_field_not_value() -> None:
    data = profile_data()
    data["skills"] = [*data["skills"], {"name": "Kubernetes"}]

    with pytest.raises(CheckFailed) as failed:
        check_profile_facts("profil", data)

    assert "skills.5" in str(failed.value)
    assert "Kubernetes" not in str(failed.value)


def test_missing_experience_is_refused() -> None:
    data = profile_data()
    data["experiences"] = data["experiences"][:1]
    with pytest.raises(CheckFailed):
        check_profile_facts("profil", data)


def test_skill_without_level_is_refused() -> None:
    nodes: list[dict[str, Any]] = [{"name": "Python", "level": "declare"}, {"name": "Docker"}]
    with pytest.raises(CheckFailed, match=r"skills\.1"):
        skills_below_declared("profil", ["Python", "Docker"], nodes)


def test_keyword_not_in_the_posting_is_refused() -> None:
    assert keywords_in_text("offre", {"keywords": [{"term": "LangGraph"}, {"term": "rag"}]}) == 2
    with pytest.raises(CheckFailed, match="rangs 1"):
        keywords_in_text("offre", {"keywords": [{"term": "Python"}, {"term": "Kubernetes"}]})
    with pytest.raises(CheckFailed):
        keywords_in_text("offre", {"keywords": []})


def test_logs_with_personal_data_are_refused() -> None:
    assert check_logs("journaux", "Capture lancée : session s1\nOffre prête : offre o1") == 2
    for leak in (
        "Camille Exemple",
        "camille.exemple@example.org",
        "Société Fictive",
        *POSTING_SENTENCES,
    ):
        with pytest.raises(CheckFailed) as failed:
            check_logs("journaux", f"ligne\n{leak}")
        assert leak not in str(failed.value)
