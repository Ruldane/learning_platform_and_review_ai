"""Étapes « tout » du contrôle de fin de phase 5 contre une fausse API qui note les appels : les
bonnes réponses lues au second passage du quiz, le bilan hebdomadaire (calendrier, bilan déjà
écrit, réglages remis), une question inattendue et une replanification sans proposition."""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from scripts import phase5_weekly
from scripts.phase4_rules import CheckFailed
from scripts.phase5_drive import drive
from scripts.phase5_quiz import QUIZ_ANSWER, build_answers, known_answers, play_quiz
from scripts.phase5_replan import replan_week
from scripts.phase5_steps import Etude
from scripts.phase5_weekly import weekly_review
from tests.scripts.phase5_fakes import FakeApi

PARIS = ZoneInfo("Europe/Paris")


def quiz_view(attempts: list[dict[str, Any]]) -> dict[str, Any]:
    kinds = ["qcm", "short", "code", "explain"] * 2
    questions = [
        {
            "id": f"q{n}",
            "rank": n,
            "type": kind,
            "prompt": "Énoncé",
            "code": "x = 1" if kind == "code" else None,
            # l'ordre des choix change d'un essai à l'autre
            "choices": ["B", "A", "C"] if kind == "qcm" else [],
        }
        for n, kind in enumerate(kinds, start=1)
    ]
    return {"status": "ready", "questions": questions, "attempts": attempts}


def graded(score: int, passed: bool) -> dict[str, Any]:
    results = [
        {
            "question_id": f"q{n}",
            "points": 1.0 if passed else 0.5,
            "correct_answer": "A" if n in (1, 5) else f"Réponse {n}",
            "explanation": "Parce que.",
            "feedback": "",
        }
        for n in range(1, 9)
    ]
    done = {"status": "graded", "score": score, "passed": passed, "results": results}
    return done | {"followup": None if passed else {"revision_tasks": [], "retry_on": None}}


def quiz_api(attempts: list[dict[str, Any]], second: dict[str, Any]) -> FakeApi:
    return FakeApi(
        {
            ("GET", "/settings"): {"timezone": "Europe/Paris"},
            ("POST", "/modules/m1/quiz"): {"quiz_id": "z1"},
            ("GET", "/quizzes/z1"): quiz_view(attempts),
            ("GET", "/quizzes/z1/attempts/a0"): graded(35, False),
            ("POST", "/quizzes/z1/attempts"): {"attempt_id": "a1", "session_id": "s1"},
            ("GET", "/quizzes/z1/attempts/a1"): second,
        }
    )


def etude() -> Etude:
    return Etude(lessons={"l1": "m1"}, lesson_id="l1")


def test_the_first_pass_answers_without_knowing_the_right_ones() -> None:
    answers = build_answers(quiz_view([]), {})

    assert answers[0] == {"question_id": "q1", "choice": 0}
    assert answers[1] == {"question_id": "q2", "text": QUIZ_ANSWER}


def test_the_right_answers_are_found_by_text_among_shuffled_choices() -> None:
    known = {"q1": "A", "q2": "Réponse 2", "q5": "A"}
    answers = build_answers(quiz_view([]), known)

    assert answers[0] == {"question_id": "q1", "choice": 1}  # « A » est le 2e choix mélangé
    assert answers[1] == {"question_id": "q2", "text": "Réponse 2"}
    assert answers[2] == {"question_id": "q3", "text": QUIZ_ANSWER}


async def test_the_second_pass_reads_the_right_answers_of_the_last_graded_attempt() -> None:
    old: list[dict[str, Any]] = [
        {"id": "a0", "status": "graded", "score": 35, "created_at": "2026-11-11T10:00:00Z"},
        {"id": "ax", "status": "failed", "score": None, "created_at": "2026-11-12T10:00:00Z"},
    ]
    api = quiz_api(old, graded(100, True))
    client, run = api.run()
    async with client:
        state = etude()
        await play_quiz(run, state)

    sent = api.sent("POST", "/quizzes/z1/attempts")[0]["answers"]
    assert sent[0] == {"question_id": "q1", "choice": 1}
    assert sent[1] == {"question_id": "q2", "text": "Réponse 2"}
    assert (state.passed, state.attempt_id) == (True, "a1")


async def test_the_first_pass_is_usually_missed_and_keeps_the_retry_day() -> None:
    api = quiz_api(
        [], graded(35, False) | {"followup": {"revision_tasks": ["t"], "retry_on": None}}
    )
    client, run = api.run()
    async with client:
        with pytest.raises(CheckFailed, match="J\\+2 attendu"):
            await play_quiz(run, etude())

    assert api.sent("GET", "/quizzes/z1/attempts/a0") == []  # rien à lire : premier passage


async def test_no_graded_attempt_means_no_known_answers() -> None:
    api = quiz_api([], {})
    client, run = api.run()
    failed = [{"id": "ax", "status": "failed", "score": None, "created_at": "x"}]
    async with client:
        assert await known_answers(run, etude(), quiz_view(failed)) == {}


# --- Bilan hebdomadaire -------------------------------------------------------------------------

SETTINGS = {"timezone": "Europe/Paris", "weekly_review": {"day": "sunday", "time": "18:00"}}
WEEKS = {"weeks": [{"start_date": "2026-11-16"}, {"start_date": "2026-11-23"}]}


def weekly_api(over: dict[tuple[str, str], Any] | None = None) -> FakeApi:
    routes: dict[tuple[str, str], Any] = {
        ("GET", "/settings"): SETTINGS,
        ("PUT", "/settings"): SETTINGS,
        ("GET", "/programs/p1"): WEEKS,
        ("GET", "/journal"): {"entries": [], "next_before": None},
        ("GET", "/sessions"): [],
    }
    return FakeApi(routes | (over or {}))


def at(monkeypatch: pytest.MonkeyPatch, moment: datetime) -> None:
    monkeypatch.setattr(phase5_weekly, "local_now", lambda zone: moment)
    monkeypatch.setattr(phase5_weekly, "POLL_WEEKLY_S", 0.01)


async def test_a_review_the_calendar_cannot_write_is_refused_before_touching_the_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    at(monkeypatch, datetime(2026, 11, 13, 10, 0, tzinfo=PARIS))  # avant le programme
    api = weekly_api()
    client, run = api.run()
    async with client:
        with pytest.raises(CheckFailed, match="commence le 2026-11-16.*2026-11-22") as caught:
            await weekly_review(run, etude())

    assert caught.value.step == "bilan hebdomadaire"
    assert api.sent("PUT", "/settings") == []


async def test_a_review_already_written_today_is_not_replayed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    at(monkeypatch, datetime(2026, 11, 22, 18, 30, tzinfo=PARIS))
    today = {"entries": [{"id": "r0", "occurred_on": "2026-11-22"}], "next_before": None}
    session = {"id": "s0", "subject_id": "p1", "created_at": "2026-11-22T17:05:00Z"}
    api = weekly_api({("GET", "/journal"): today, ("GET", "/sessions"): [session]})
    client, run = api.run()
    async with client:
        state = etude()
        await weekly_review(run, state)

    assert state.review_entry_id is None
    assert api.sent("PUT", "/settings") == []


async def test_a_review_already_written_without_any_replan_session_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    at(monkeypatch, datetime(2026, 11, 22, 18, 30, tzinfo=PARIS))
    today = {"entries": [{"id": "r0", "occurred_on": "2026-11-22"}], "next_before": None}
    api = weekly_api({("GET", "/journal"): today})
    client, run = api.run()
    async with client:
        with pytest.raises(CheckFailed, match="aucune session `replan`"):
            await weekly_review(run, etude())


async def test_the_settings_come_back_even_when_the_review_never_comes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    at(monkeypatch, datetime(2026, 11, 22, 18, 30, tzinfo=PARIS))
    monkeypatch.setattr(phase5_weekly, "WEEKLY_LAUNCH_S", 0.05)
    api = weekly_api()
    client, run = api.run()
    async with client:
        with pytest.raises(CheckFailed, match="Aucune entrée en 0 s"):
            await weekly_review(run, etude())

    puts = api.sent("PUT", "/settings")
    assert [p["weekly_review"] for p in puts] == [
        {"day": "sunday", "time": "18:29"},  # un jour local, l'heure moins une minute
        {"day": "sunday", "time": "18:00"},  # remis comme avant
    ]


# --- Sessions d'agents --------------------------------------------------------------------------


def waiting(kind: str) -> dict[str, Any]:
    return {"status": "waiting_user", "pending_interrupt": {"interrupt_id": "i1", "kind": kind}}


async def test_a_question_nobody_expected_stops_the_session_driver() -> None:
    api = FakeApi({("GET", "/sessions/s1"): waiting("capture_task")})
    client, run = api.run()
    async with client:
        with pytest.raises(CheckFailed, match="Question « capture_task » inattendue"):
            await drive(run, "capture", "s1", {"capture_text": lambda question: "x"})


async def test_a_replan_that_ends_without_a_proposal_names_the_last_version() -> None:
    api = FakeApi(
        {
            ("GET", "/settings"): SETTINGS,
            ("GET", "/programs/p1"): {"version": 1, "weeks": []},
            ("POST", "/programs/p1/replan"): {"session_id": "s1"},
            ("GET", "/sessions/s1"): {"status": "completed", "pending_interrupt": None},
            ("GET", "/programs/p1/versions"): [{"version": 2, "status": "impossible"}],
        }
    )
    client, run = api.run()
    async with client:
        with pytest.raises(CheckFailed, match="dernière version : 2 impossible"):
            await replan_week(run, etude())

    assert api.sent("POST", "/programs/p1/replan") == [
        {"available_minutes": 300, "message": "cette semaine je n'ai que 5 heures"}
    ]
