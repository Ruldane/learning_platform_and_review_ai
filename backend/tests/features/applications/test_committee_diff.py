"""L'avant et l'après du comité (D147, F19) : pur, sans base. Objections comparées après
normalisation, la même à partir de 0,85 de ressemblance."""

import pytest

from app.features.applications.service.committee_diff import committee_diff, same_objection
from tests.features.applications.committee_support import votes_of


@pytest.mark.parametrize(
    ("first", "second", "same"),
    [
        ("Aucun mot clé LangGraph dans le CV", "aucun mot-clé LangGraph dans le CV.", True),
        ("Aucun mot clé LangGraph dans le CV", "Aucun mot clé LangGraph dans votre CV", True),
        ("Pas d'agent mis en production", "PAS D'AGENT MIS EN PRODUCTION !", True),
        ("Résultat chiffré enfoui", "Parcours peu lisible sur une page", False),
        ("Pas d'expérience en production", "Aucun diplôme en informatique", False),
        ("Peu de travail d'équipe visible", "", False),
    ],
)
def test_same_objection(first: str, second: str, same: bool) -> None:
    assert same_objection(first, second) is same
    assert same_objection(second, first) is same


def test_diff_votes_before_after() -> None:
    diff = committee_diff(
        "prev",
        votes_of("non", "non", "peut_etre", "non"),
        votes_of("oui", "non", "oui", "peut_etre"),
        [],
        [],
    )
    assert diff.previous_id == "prev"
    assert [(v.persona, v.before, v.after) for v in diff.votes] == [
        ("ats_reader", "non", "oui"),
        ("recruiter", "non", "non"),
        ("manager", "peut_etre", "oui"),
        ("colleague", "non", "peut_etre"),
    ]


def test_diff_objections_resolved_and_new() -> None:
    before = ["Aucun mot clé LangGraph dans le CV", "Résultat chiffré enfoui", "Peu d'équipe"]
    after = ["Aucun mot-clé LangGraph dans le CV !", "Pas d'agent en production"]
    diff = committee_diff(
        "prev",
        votes_of("oui", "oui", "oui", "oui"),
        votes_of("oui", "oui", "oui", "oui"),
        before,
        after,
    )
    assert diff.objections_resolved == ["Résultat chiffré enfoui", "Peu d'équipe"]
    assert diff.objections_new == ["Pas d'agent en production"]


def test_diff_without_changes_is_empty() -> None:
    votes = votes_of("oui", "non", "non", "oui")
    diff = committee_diff("prev", votes, votes, ["Même objection"], ["Même objection"])
    assert diff.objections_resolved == [] and diff.objections_new == []
    assert all(v.before == v.after for v in diff.votes)
