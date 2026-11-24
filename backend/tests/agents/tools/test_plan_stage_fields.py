"""Étape, justification, pages officielles et API anciennes : facultatives et bornées."""

import copy
from typing import Any

import pytest
from pydantic import ValidationError

from app.agents.tools.plan_schema import PlanDraft

TASK = {"title": "Lire la doc", "type": "lire", "minutes": 30, "done_criterion": "Notes prises"}
MODULE: dict[str, Any] = {"title": "Modèles et messages", "skills": ["LangChain"], "tasks": [TASK]}
PLAN: dict[str, Any] = {
    "title": "LangChain de zéro à expert",
    "skills": [{"name": "LangChain", "domain": "Agents"}],
    "weeks": [
        {
            "theme": "Les bases",
            "objective": "Appeler un modèle",
            "deliverable": "Un script",
            "modules": [MODULE],
        }
    ],
}


def plan(**week: Any) -> dict[str, Any]:
    data = copy.deepcopy(PLAN)
    data["weeks"][0].update(week)
    return data


def with_module(**fields: Any) -> dict[str, Any]:
    data = copy.deepcopy(PLAN)
    data["weeks"][0]["modules"][0].update(fields)
    return data


def test_the_new_fields_are_optional() -> None:
    draft = PlanDraft.model_validate(PLAN)
    week = draft.weeks[0]
    assert week.stage is None and week.rationale is None
    assert week.modules[0].official_urls == [] and week.modules[0].legacy == []


def test_legacy_stage_is_normalized_and_the_rationale_is_kept() -> None:
    draft = PlanDraft.model_validate(
        plan(stage="pratique", rationale="Les outils viennent après les messages.")
    )
    assert draft.weeks[0].stage == "practice"
    assert draft.weeks[0].rationale == "Les outils viennent après les messages."


@pytest.mark.parametrize("stage", ["debutant", "", "Fondations"])
def test_unknown_stage_is_refused(stage: str) -> None:
    with pytest.raises(ValidationError):
        PlanDraft.model_validate(plan(stage=stage))


def test_rationale_is_refused_when_too_short_and_shortened_when_too_long() -> None:
    with pytest.raises(ValidationError):
        PlanDraft.model_validate(plan(rationale="ab"))
    long = PlanDraft.model_validate(plan(rationale="Une raison. " * 40))
    assert len(long.weeks[0].rationale or "") <= 300


def test_official_urls_are_http_and_at_most_three() -> None:
    urls = [f"https://docs.exemple.org/page{n}" for n in range(3)]
    draft = PlanDraft.model_validate(with_module(official_urls=urls))
    assert draft.weeks[0].modules[0].official_urls == urls
    for bad in (
        urls + ["https://docs.exemple.org/4"],
        ["ftp://docs.exemple.org/a"],
        ["pas une url"],
    ):
        with pytest.raises(ValidationError):
            PlanDraft.model_validate(with_module(official_urls=bad))


def test_legacy_entries_are_bounded() -> None:
    draft = PlanDraft.model_validate(with_module(legacy=["LCEL", "LLMChain"]))
    assert draft.weeks[0].modules[0].legacy == ["LCEL", "LLMChain"]
    for bad in (["a"], ["x" * 121], ["LCEL"] * 6):
        with pytest.raises(ValidationError):
            PlanDraft.model_validate(with_module(legacy=bad))


def test_a_refused_value_is_never_named_in_the_error() -> None:
    secret = "ftp://secret.exemple.org/privé"
    with pytest.raises(ValidationError) as caught:
        PlanDraft.model_validate(with_module(official_urls=[secret]))
    assert secret not in str(caught.value.errors(include_input=False))
