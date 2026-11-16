"""Règles pures de la partie `projets` du contrôle de la phase 8 : choix du projet, énoncé,
évaluation, brouillons, compétences, profil, textes cherchés dans les journaux. Aucun réseau."""

import copy
import re
from typing import Any

import pytest

from scripts.phase4_rules import CheckFailed
from scripts.phase8_projects_rules import (
    REPO_URL,
    build_description,
    check_brief,
    check_drafts,
    check_entry_added,
    check_evaluation,
    check_redo,
    check_skills,
    check_submission,
    pick_project,
    profile_view,
    project_extras,
    readme_phrases,
    status_counts,
)
from tests.scripts.phase8_projects_support import (
    BRIEF,
    ENTRY,
    README_LINE,
    SKILLS,
    TITLE,
    drafts,
    evaluation,
    project_json,
)

STEP = "suites"


def reviewed(met: list[bool], **over: Any) -> dict[str, Any]:
    status = "validated" if all(met) else "to_redo"
    return project_json(status=status, evaluation=evaluation(met), **over)


# -- choix du projet --------------------------------------------------------------------------


def test_pick_prefers_a_written_brief_then_a_pending_one_then_a_failed_one() -> None:
    todo, redo = project_json("a", "todo"), project_json("b", "to_redo")
    pending, failed = project_json("c", "brief_pending"), project_json("d", "brief_failed")

    assert pick_project([failed, pending, redo, todo]) == (todo, "ready")
    assert pick_project([failed, pending, redo]) == (redo, "ready")
    assert pick_project([failed, pending]) == (pending, "wait")
    assert pick_project([failed]) == (failed, "retry")


def test_pick_takes_the_earliest_of_the_program() -> None:
    late = project_json("a", week=3, rank=1)
    early = project_json("b", week=1, rank=2)
    first = project_json("c", week=1, rank=1)

    assert pick_project([late, early, first])[0] == first


def test_pick_skips_validated_and_reviewing_projects_and_counts_the_statuses() -> None:
    projects = [
        project_json("a", "validated"),
        project_json("b", "validated"),
        project_json("c", "reviewing"),
    ]

    assert pick_project(projects) == (None, "none")
    assert status_counts(projects) == "reviewing 1, validated 2"
    assert status_counts([]) == "aucun"


# -- énoncé et rendu --------------------------------------------------------------------------


def test_a_complete_brief_reports_its_criteria_and_hours() -> None:
    assert check_brief("énoncé", BRIEF) == (3, 4)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"criteria": ["a", "b"]}, "2 critère(s)"),
        ({"criteria": list("abcdefg")}, "7 critère(s)"),
        ({"criteria": ["a", " ", "c"]}, "critère de l'énoncé est vide"),
        ({"hours": 2}, "2 h annoncées"),
        ({"hours": 7}, "7 h annoncées"),
        ({"objective": "  "}, "objective"),
    ],
)
def test_a_brief_out_of_bounds_is_refused(change: dict[str, Any], message: str) -> None:
    with pytest.raises(CheckFailed, match=re.escape(message)):
        check_brief("énoncé", BRIEF | change)
    with pytest.raises(CheckFailed, match="absent"):
        check_brief("énoncé", None)


def test_the_description_names_every_criterion_and_stays_under_the_limit() -> None:
    text = build_description(BRIEF)

    assert all(criterion in text for criterion in BRIEF["criteria"])
    assert len(build_description(BRIEF | {"objective": "x" * 9000})) <= 3900


def test_the_last_submission_must_be_the_one_sent() -> None:
    sent = {"at": "t", "repo_url": REPO_URL, "description": "d", "screenshots": 0}

    assert check_submission("rendu", {"submissions": [sent, sent]}, "d") == 2
    for bad in ({"description": "autre"}, {"repo_url": "https://x.example"}, {"screenshots": 1}):
        with pytest.raises(CheckFailed):
            check_submission("rendu", {"submissions": [sent | bad]}, "d")
    with pytest.raises(CheckFailed, match="Aucun rendu"):
        check_submission("rendu", {"submissions": []}, "d")


# -- évaluation -------------------------------------------------------------------------------


def test_a_validated_evaluation_reports_its_numbers() -> None:
    assert check_evaluation("évaluation", reviewed([True, True, True])) == {
        "verdict": "validated",
        "met": 3,
        "total": 3,
        "repo": "read",
    }
    assert check_evaluation("évaluation", reviewed([True, False, True]))["met"] == 2


def test_an_evaluation_is_refused_when_the_code_rules_do_not_hold() -> None:
    def refused(project: dict[str, Any], message: str) -> None:
        with pytest.raises(CheckFailed, match=message):
            check_evaluation("évaluation", project)

    refused(project_json(status="to_redo"), "Aucune évaluation")
    wrong_status = reviewed([True, True, True]) | {"status": "to_redo"}
    refused(wrong_status, "Statut")
    lying = reviewed([True, False, True])
    lying["evaluation"]["verdict"] = "validated"
    refused(lying, "incohérent")
    missing = reviewed([True, True, True])
    missing["evaluation"]["results"].pop()
    refused(missing, "2 résultat")
    duplicate = reviewed([True, True, True])
    duplicate["evaluation"]["results"][2]["index"] = 1
    refused(duplicate, "rangs inexacts")
    unread = reviewed([True, True, True])
    unread["evaluation"]["repo_status"] = "unreadable"
    refused(unread, "unreadable")
    silent = reviewed([True, True, True])
    silent["evaluation"]["feedback"] = " "
    refused(silent, "Retour")


# -- suites : brouillons, compétences, reprise ------------------------------------------------


def test_drafts_are_four_of_each_kind_or_none() -> None:
    assert check_drafts(STEP, {"drafts": drafts()}) == (3, 1)
    assert check_drafts(STEP, {"drafts": []}) == (0, 0)  # « brouillons indisponibles »


@pytest.mark.parametrize(
    "found",
    [drafts()[:3], [*drafts()[:3], drafts()[0]], [{**d, "status": "nope"} for d in drafts()]],
)
def test_incomplete_or_unknown_drafts_are_refused(found: list[dict[str, Any]]) -> None:
    with pytest.raises(CheckFailed):
        check_drafts(STEP, {"drafts": found})


def test_an_empty_draft_is_refused() -> None:
    found = drafts()
    found[0] = {**found[0], "content": " "}
    with pytest.raises(CheckFailed, match="vide"):
        check_drafts(STEP, {"drafts": found})


def _graph(*levels: str | None) -> dict[str, Any]:
    nodes = [
        {"id": f"k{n}", "name": n_, "level": lv}
        for n, (n_, lv) in enumerate(zip(SKILLS, levels, strict=True))
    ]
    return {"nodes": nodes}


def test_every_module_skill_must_be_proven_on_the_map() -> None:
    names = ["flask", "TESTS automatisés"]  # même clé que le back : sans casse ni accents

    assert check_skills(STEP, _graph("prouve", "prouve"), names) == 2
    with pytest.raises(CheckFailed, match="1 compétence\\(s\\) sur 2"):
        check_skills(STEP, _graph("prouve", "valide"), names)
    with pytest.raises(CheckFailed, match="2 compétence"):
        check_skills(STEP, {"nodes": []}, names)
    with pytest.raises(CheckFailed, match="sans compétence"):
        check_skills(STEP, _graph("prouve", "prouve"), [])


def test_a_project_to_redo_names_its_unmet_criteria_and_carries_no_draft() -> None:
    assert check_redo(STEP, reviewed([True, False, False])) == 2
    with pytest.raises(CheckFailed, match="aucun brouillon"):
        check_redo(STEP, reviewed([True, False, True]) | {"drafts": drafts()})
    with pytest.raises(CheckFailed, match="aucun critère non atteint"):
        check_redo(STEP, reviewed([True, True, True]))
    nameless = reviewed([True, False, True])
    nameless["evaluation"]["results"][1]["criterion"] = ""
    with pytest.raises(CheckFailed, match="pas nommé"):
        check_redo(STEP, nameless)


# -- profil -----------------------------------------------------------------------------------


def _state(version: int, *names: str, draft: Any = None) -> dict[str, Any]:
    data = {"projects": [{"name": name} for name in names]}
    return {"validated": {"version": version, "data": data}, "draft": draft}


def test_the_profile_view_needs_a_validated_profile_without_a_pending_draft() -> None:
    assert profile_view(STEP, _state(3, "A", "B")) == (3, ["A", "B"])
    with pytest.raises(CheckFailed, match="Aucun profil"):
        profile_view(STEP, {"validated": None, "draft": None})
    with pytest.raises(CheckFailed, match="brouillon de profil"):
        profile_view(STEP, _state(3, draft={"version": 4}))


def test_the_entry_is_added_once_with_exactly_one_more_version() -> None:
    before = (3, ["A"])

    check_entry_added(STEP, before, (4, ["A", "N"]), "N", 4)
    check_entry_added(STEP, (3, ["N"]), (4, ["N", "N"]), "N", 4)  # un homonyme déjà là
    for after, recorded, message in (
        ((3, ["A", "N"]), 3, "version 3"),
        ((5, ["A", "N"]), 5, "version 5"),
        ((4, ["A"]), 4, "une seule fois"),
        ((4, ["A", "X"]), 4, "une seule fois"),
        ((4, ["A", "N", "N"]), 4, "une seule fois"),
        ((4, ["A", "N"]), None, "ne note pas"),
    ):
        with pytest.raises(CheckFailed, match=message):
            check_entry_added(STEP, before, after, "N", recorded)


# -- journaux ---------------------------------------------------------------------------------


def test_readme_phrases_keep_long_prose_lines_only() -> None:
    text = (
        "# Requests\n\n[![badge](https://x.example/b.svg)](https://x.example)\n"
        f"{README_LINE}\nTrop court.\n"
        "Voir https://docs.example/long pour une ligne avec un lien dedans.\n"
        f"{README_LINE}\n"
    )

    assert readme_phrases(text) == [README_LINE]
    many = "\n".join(
        f"Une ligne de prose numéro {n} assez longue pour être gardée." for n in range(12)
    )
    assert len(readme_phrases(many)) == 5


def test_project_extras_gather_this_runs_texts_once_and_skip_the_short_ones() -> None:
    project = reviewed([True, True, True], drafts=drafts())
    project["brief"] = copy.deepcopy(BRIEF)

    extras = project_extras(project, "Ma description fictive.", [README_LINE])

    for text in (
        project["title"],
        TITLE,
        REPO_URL,
        "Ma description fictive.",
        BRIEF["criteria"][0],
        BRIEF["objective"],
        "Commentaire du critère 1.",
        "Brouillon cv_line.",
        ENTRY["description"],
        README_LINE,
    ):
        assert extras.count(text) == 1, text
    assert "Brouillon" not in extras and all(len(text) >= 4 for text in extras)
    assert project_extras({}, "", []) == [REPO_URL]
