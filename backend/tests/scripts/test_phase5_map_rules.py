"""Règles de la carte du contrôle de fin de phase 5 : chacune a son cas d'échec, et un message ne
nomme jamais une compétence."""

from datetime import date
from typing import Any

import pytest

from scripts.phase4_rules import CheckFailed
from scripts.phase5_map_rules import (
    SkillState,
    check_detail,
    check_history,
    check_states,
    module_skill_names,
    norm_skill,
    read_states,
)

STEP = "carte après"
PROGRAM = {"weeks": [{"modules": [{"id": "m1", "skills": ["Séries", "pandas"]}]}]}
GRAPH = {
    "nodes": [
        {"id": "s1", "name": "series", "level": "en_cours", "evidence_count": 3},
        {"id": "s2", "name": "Autre", "level": "valide", "evidence_count": 9},
    ]
}


def state(level: str | None = "en_cours", evidence: int = 1) -> SkillState:
    return SkillState("s1", level, evidence)


def test_skill_names_are_matched_like_the_back() -> None:
    assert norm_skill("  Séries temporelles. ") == "series temporelles"
    assert module_skill_names(PROGRAM, "m1", STEP) == ["Séries", "pandas"]
    with pytest.raises(CheckFailed, match="m9 absent"):
        module_skill_names(PROGRAM, "m9", STEP)


def test_a_skill_the_map_does_not_know_has_no_level_and_no_proof() -> None:
    found = read_states(GRAPH, ["Séries", "pandas"])

    assert found["series"] == SkillState("s1", "en_cours", 3)
    assert found["pandas"] == SkillState("", None, 0)


def test_the_session_raises_every_skill_to_in_progress_with_one_more_proof() -> None:
    before = {"a": state(None, 0), "b": state("declare", 2)}
    check_states(STEP, before, {"a": state("en_cours", 1), "b": state("valide", 4)}, passed=False)


def test_a_passed_quiz_needs_two_proofs_and_the_validated_level() -> None:
    before = {"a": state("en_cours", 1)}

    check_states(STEP, before, {"a": state("valide", 3)}, passed=True)
    with pytest.raises(CheckFailed, match="n° 1 au niveau en_cours : valide ou prouve"):
        check_states(STEP, before, {"a": state("en_cours", 3)}, passed=True)
    with pytest.raises(CheckFailed, match=r"2 preuve\(s\), 3 au moins"):
        check_states(STEP, before, {"a": state("valide", 2)}, passed=True)


@pytest.mark.parametrize(
    ("after", "message"),
    [
        ({}, "n° 1 du module absente"),
        ({"a": SkillState("", None, 0)}, "n° 1 du module absente"),
        ({"a": state("declare", 5)}, "niveau declare"),
        ({"a": state(None, 5)}, "niveau None"),
        ({"a": state("en_cours", 1)}, r"1 preuve\(s\), 2 au moins"),
    ],
)
def test_the_map_must_show_the_session(after: dict[str, SkillState], message: str) -> None:
    with pytest.raises(CheckFailed, match=message) as caught:
        check_states(STEP, {"a": state(None, 1)}, after, passed=False)

    assert caught.value.step == STEP


def test_the_proof_count_stops_at_twenty() -> None:
    before = {"a": state("valide", 20)}
    check_states(STEP, before, {"a": state("valide", 20)}, passed=True)


def test_a_module_without_skills_is_a_failure() -> None:
    with pytest.raises(CheckFailed, match="aucune compétence"):
        check_states(STEP, {}, {}, passed=False)


def test_the_skill_page_cites_the_session_and_the_passed_quiz() -> None:
    evidence = [
        {"kind": "study", "url": "/etudier/session/e1"},
        {"kind": "quiz", "url": "/etudier/quiz/q1"},
    ]
    detail: dict[str, Any] = {"evidence": evidence}

    check_detail(STEP, detail, study_id="e1", quiz_id="q1", passed=True)
    check_detail(STEP, {"evidence": evidence[:1]}, study_id="e1", quiz_id="q1", passed=False)
    with pytest.raises(CheckFailed, match="session e2"):
        check_detail(STEP, detail, study_id="e2", quiz_id="q1", passed=False)
    with pytest.raises(CheckFailed, match="quiz q1"):
        check_detail(STEP, {"evidence": evidence[:1]}, study_id="e1", quiz_id="q1", passed=True)


def history(week: str = "2026-11-16", score: int = 25) -> dict[str, Any]:
    counts = {"declare": 0, "en_cours": 3, "valide": 0, "prouve": 0}
    return {
        "points": [
            {"week_start": "2026-11-09", "counts": counts, "score": 0},
            {"week_start": week, "counts": counts, "score": score},
        ]
    }


def test_the_last_point_of_the_history_is_the_current_week() -> None:
    weeks = {date(2026, 11, 16), date(2026, 11, 9)}  # avant et après un minuit de dimanche
    check_history(STEP, history(), weeks, 3)

    with pytest.raises(CheckFailed, match="pas la semaine en cours"):
        check_history(STEP, history("2026-11-02"), weeks, 3)
    with pytest.raises(CheckFailed, match=r"3 compétence\(s\) sur le dernier point, 4 au moins"):
        check_history(STEP, history(), weeks, 4)
    with pytest.raises(CheckFailed, match="Score nul"):
        check_history(STEP, history(score=0), weeks, 3)
    with pytest.raises(CheckFailed, match="Aucun point"):
        check_history(STEP, {"points": []}, weeks, 3)
