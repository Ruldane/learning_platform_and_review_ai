"""Étape « quiz » du contrôle de fin de phase 5 contre une fausse API : les bonnes réponses lues
au second passage, un autre module quand le quiz de la session attend son nouvel essai (J+2), et le
blocage vérifié quand aucun module n'est libre."""

from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import httpx
import pytest

from scripts.phase4_rules import CheckFailed
from scripts.phase5_quiz import QUIZ_ANSWER, build_answers, known_answers, play_quiz
from tests.scripts.phase5_fakes import FakeApi, etude, graded, quiz_api, quiz_view

FUTURE = "2099-01-01"  # toujours dans le futur
PARIS = ZoneInfo("Europe/Paris")
OLD: list[dict[str, Any]] = [
    {"id": "a0", "status": "graded", "score": 35, "created_at": "2026-11-12T09:00:00Z"}
]


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
    assert (state.passed, state.attempt_id) == (True, "a1x")


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


async def test_a_quiz_waiting_for_its_retry_gives_way_to_another_module() -> None:
    api = quiz_api(OLD, graded(100, True), retry_on={"m1": FUTURE})
    client, run = api.run()
    async with client:
        state = etude()
        await play_quiz(run, state)

    assert (state.quiz_module_id, state.quiz_id, state.passed) == ("m2", "z2", True)
    assert api.sent("POST", "/modules/m1/quiz") == []  # le quiz qui attend n'est pas touché
    assert len(api.sent("POST", "/quizzes/z2/attempts")) == 1
    assert state.module_id == "m1"  # la session reste celle du module 1


async def test_a_quiz_free_again_is_taken_even_if_it_missed_before() -> None:
    api = quiz_api(OLD, graded(100, True), retry_on={"m1": "2000-01-01"})  # le J+2 est passé
    client, run = api.run()
    async with client:
        state = etude()
        await play_quiz(run, state)

    assert (state.quiz_module_id, state.passed) == ("m1", True)


def blocked_api() -> tuple[FakeApi, str]:
    """Les deux quiz attendent ; la tentative ratée de `m1` date d'il y a une heure : son nouvel
    essai est J+2 local."""
    created = datetime.now(UTC) - timedelta(hours=1)
    retry_on = (created.astimezone(PARIS).date() + timedelta(days=2)).isoformat()
    attempts = [{"id": "a0", "status": "graded", "score": 35, "created_at": created.isoformat()}]
    api = quiz_api(attempts, {}, retry_on={"m1": retry_on, "m2": FUTURE})
    followup = {"revision_tasks": ["t"], "unplaced": 0, "retry_on": retry_on}
    api.routes[("GET", "/quizzes/z1/attempts/a0")] = graded(35, False) | {
        "id": "a0",
        "followup": followup,
    }
    refused = httpx.Response(409, json={"error": {"code": "retry_too_soon"}})
    api.routes[("POST", "/quizzes/z1/attempts")] = refused
    return api, retry_on


async def test_when_every_quiz_waits_the_block_is_checked_without_a_new_attempt() -> None:
    api, retry_on = blocked_api()
    client, run = api.run()
    async with client:
        state = etude()
        await play_quiz(run, state)

    assert (state.quiz_blocked, state.quiz_id, state.retry_on) == (True, "z1", retry_on)
    assert (state.attempt_id, state.passed) == ("", False)
    assert len(api.sent("POST", "/quizzes/z1/attempts")) == 1  # l'essai refusé, 409
    assert api.sent("POST", "/modules/m1/quiz") == []


async def test_a_block_the_back_does_not_enforce_is_a_failure() -> None:
    api, _ = blocked_api()
    api.routes[("POST", "/quizzes/z1/attempts")] = {"attempt_id": "a9", "session_id": "s"}
    client, run = api.run()
    async with client:
        with pytest.raises(CheckFailed, match="Nouvel essai accepté avant le"):
            await play_quiz(run, etude())


async def test_a_block_refused_for_another_reason_is_a_failure() -> None:
    api, _ = blocked_api()
    api.routes[("POST", "/quizzes/z1/attempts")] = httpx.Response(
        409, json={"error": {"code": "quiz_not_ready"}}
    )
    client, run = api.run()
    async with client:
        with pytest.raises(CheckFailed, match="quiz_not_ready"):
            await play_quiz(run, etude())


async def test_a_block_with_the_wrong_retry_day_is_a_failure() -> None:
    api, _ = blocked_api()
    api.routes[("GET", "/programs/p1/quizzes")] = [
        {"module_id": "m1", "quiz_id": "z1", "status": "ready", "retry_on": "2099-01-02"},
        {"module_id": "m2", "quiz_id": "z2", "status": "ready", "retry_on": FUTURE},
    ]
    client, run = api.run()
    async with client:
        with pytest.raises(CheckFailed, match=r"J\+2 attendu"):
            await play_quiz(run, etude())
