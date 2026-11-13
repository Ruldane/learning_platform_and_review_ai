"""Règles du planning, du bilan hebdomadaire et du journal du contrôle de fin de phase 5."""

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from scripts.phase4_rules import CheckFailed
from scripts.phase5_plan_rules import (
    JournalWant,
    capped_start,
    check_accepted,
    check_journal,
    check_pending,
    feasible_minutes,
    local_target,
    review_blocker,
    week_cap,
)

CAP = 255
MONDAY = date(2026, 11, 16)
PARIS = ZoneInfo("Europe/Paris")


def loads(*rows: tuple[int, int, int]) -> list[dict[str, Any]]:
    """`(rang, après, plafond)` ; les semaines se suivent depuis le 16/11."""
    return [
        {"rank": rank, "start_date": f"2026-11-{16 + 7 * (rank - 1)}", "after": after, "cap": cap}
        for rank, after, cap in rows
    ]


def proposal(**over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "version": 2,
        "kind": "replan",
        "status": "pending",
        "session_id": "s1",
        "accepted_at": None,
        "diff": {"moved": [], "removed": [], "added": []},
        "week_loads": loads((1, 250, CAP), (2, 600, 714)),
    }
    return base | over


PROGRAM = {"cap_minutes": 714, "version": 1, "weeks": []}


def test_a_proposal_shows_one_week_capped_by_january() -> None:
    check_pending(proposal(), PROGRAM, "s1", CAP)
    assert capped_start(proposal(), CAP) == MONDAY


@pytest.mark.parametrize(
    ("over", "message"),
    [
        ({"status": "impossible"}, "replan/impossible"),
        ({"kind": "build"}, "build/pending"),
        ({"session_id": "s9"}, "session s9"),
        ({"diff": None}, "sans avant / après"),
        ({"week_loads": []}, "sans avant / après"),
        ({"week_loads": loads((1, 250, 714))}, r"0 semaine\(s\) plafonnée\(s\) à 255"),
        ({"week_loads": loads((1, 256, CAP))}, "Semaine 1 à 256 min, plafond 255"),
        ({"week_loads": loads((1, 200, CAP), (2, 715, 714))}, "Semaine 2 à 715 min, plafond 714"),
    ],
)
def test_a_wrong_proposal_is_refused(over: dict[str, Any], message: str) -> None:
    with pytest.raises(CheckFailed, match=message) as caught:
        check_pending(proposal(**over), PROGRAM, "s1", CAP)

    assert caught.value.step == "replanification"


def accepted(version: int = 2, **over: Any) -> dict[str, Any]:
    return {"version": version, "status": "accepted", "accepted_at": "2026-11-18T10:00:00Z"} | over


def program(version: int, *week_loads: int) -> dict[str, Any]:
    """Un programme à `version`, une semaine par charge (lundi 16/11, 23/11…)."""
    weeks = [
        {"rank": n, "start_date": f"2026-11-{9 + 7 * n}", "load_minutes": load}
        for n, load in enumerate(week_loads, start=1)
    ]
    return {"version": version, "cap_minutes": 714, "weeks": weeks}


def test_an_accepted_proposal_becomes_the_version_of_the_program() -> None:
    check_accepted(accepted(), program(2, 250, 600), before=1, capped=MONDAY, cap_week=CAP)
    # des propositions closes entre-temps ont pris des numéros : le programme prend le dernier
    check_accepted(accepted(4), program(4, 250), before=1, capped=MONDAY, cap_week=CAP)


@pytest.mark.parametrize(
    ("version", "prog", "message"),
    [
        (accepted(status="pending"), program(2), "pending : `accepted` attendu"),
        (accepted(accepted_at=None), program(2), "`accepted` attendu"),
        (accepted(), program(1), "Programme à la version 1, version acceptée 2"),
        (accepted(), program(3), "Programme à la version 3, version acceptée 2"),
        (accepted(1), program(1), "après la 1"),
        (accepted(), program(2, 250, 715), "Semaine 2 à 715 min, plafond 714"),
        (accepted(), program(2, 256), "Semaine 1 à 256 min, plafond 255"),
    ],
)
def test_a_proposal_not_applied_is_refused(
    version: dict[str, Any], prog: dict[str, Any], message: str
) -> None:
    with pytest.raises(CheckFailed, match=message):
        check_accepted(version, prog, before=1, capped=MONDAY, cap_week=CAP)


def test_five_hours_cap_the_week_at_255() -> None:
    assert week_cap(300) == 255
    assert week_cap(360) == 306


def week_of_tasks(*tasks: tuple[str, str, int]) -> dict[str, Any]:
    items = [{"planned_date": day, "status": s, "minutes": m} for day, s, m in tasks]
    return {"weeks": [{"start_date": "2026-11-16", "modules": [{"tasks": items}]}]}


def test_five_hours_stay_five_hours_when_the_week_has_room() -> None:
    done = week_of_tasks(("2026-11-17", "done", 190), ("2026-11-18", "todo", 500))
    assert feasible_minutes(done, date(2026, 11, 18)) == 300  # 190 + 65 = 255


def test_a_full_week_asks_for_the_least_minutes_that_keep_a_practice_and_a_quiz() -> None:
    done = week_of_tasks(("2026-11-17", "done", 240))  # 240 + 65 = 305 : 360 min donnent 306
    assert feasible_minutes(done, date(2026, 11, 18)) == 360


def test_a_program_not_begun_is_capped_on_its_first_week() -> None:
    done = week_of_tasks(("2026-11-17", "done", 100))
    assert feasible_minutes(done, date(2026, 11, 10)) == 300


def test_the_weekly_review_is_set_one_minute_before_now() -> None:
    assert local_target(datetime(2026, 11, 22, 18, 30, tzinfo=PARIS)) == ("sunday", "18:29")
    just_after_midnight = datetime(2026, 11, 23, 0, 0, 30, tzinfo=PARIS)
    assert local_target(just_after_midnight) == ("sunday", "23:59")


def test_a_review_needs_a_program_that_covers_the_week_it_reads_and_a_week_after() -> None:
    starts = [MONDAY, date(2026, 11, 23)]
    assert review_blocker(starts, date(2026, 11, 22)) is None  # dimanche : la semaine 1
    assert review_blocker(starts, date(2026, 11, 25)) is None  # mercredi : la semaine 1 relue
    assert "Aucune semaine après" in (review_blocker(starts, date(2026, 11, 29)) or "")
    blocked = review_blocker(starts, date(2026, 11, 13))
    assert blocked and "commence le 2026-11-16" in blocked and "2026-11-22" in blocked
    assert "Aucune semaine après" in (review_blocker(starts, date(2026, 12, 6)) or "")


def entry(kind: str, entry_id: str = "e", **links: str) -> dict[str, Any]:
    base = {"session_id": None, "study_session_id": None, "quiz_attempt_id": None}
    return {"id": entry_id, "kind": kind, "links": base | links}


def journal() -> list[dict[str, Any]]:
    return [
        entry("study_session", study_session_id="e1"),
        entry("quiz", quiz_attempt_id="a1"),
        entry("capture", session_id="c1"),
        entry("capture", session_id="c2"),
        entry("weekly_review", "r1"),
    ]


def test_the_journal_shows_one_entry_of_each_kind_linked_to_the_run() -> None:
    check_journal(journal(), JournalWant("e1", "a1", "r1", ["c1", "c2"]))
    check_journal(journal(), JournalWant("e1", "a1", None, ["c1"]))  # bilan déjà écrit


@pytest.mark.parametrize(
    ("want", "message"),
    [
        (JournalWant("e9", "a1", "r1"), "`study_session` pour la session e9"),
        (JournalWant("e1", "a9", "r1"), "`quiz` pour la tentative a9"),
        (JournalWant("e1", "a1", "r1", ["c9"]), "`capture` pour la session c9"),
        (JournalWant("e1", "a1", "r9"), "`weekly_review`"),
    ],
)
def test_a_missing_journal_entry_is_named(want: JournalWant, message: str) -> None:
    with pytest.raises(CheckFailed, match=message) as caught:
        check_journal(journal(), want)

    assert caught.value.step == "journal"


def test_a_journal_without_any_review_fails_even_when_any_review_would_do() -> None:
    with pytest.raises(CheckFailed, match="weekly_review"):
        check_journal(journal()[:4], JournalWant("e1", "a1", None, ["c1"]))
