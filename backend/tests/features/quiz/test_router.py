"""Routes des quiz (D101) : préparation idempotente, réponses cachées avant la note, 422 sans
écho, double envoi (Review Focus n° 5), notation interrompue, nouvel essai à J+2 avec questions
et choix mélangés (F27), isolation entre utilisateurs."""

import asyncio
from datetime import UTC, datetime

import httpx
import pytest
from fastapi import FastAPI

from app.db.models.study import QuizAttempt
from app.features.quiz.repository import AttemptRepository
from tests.features.quiz.conftest import Seeded
from tests.features.quiz.support import (
    API,
    FAIL_35,
    PASS_85,
    answers,
    count,
    grade,
    post_attempt,
    quiz_view,
    ready_quiz,
    started_attempt,
)
from tests.sessions_support import act_as


async def test_start_quiz_is_idempotent(client: httpx.AsyncClient, seeded: Seeded) -> None:
    path = f"{API}/modules/{seeded.modules[0]}/quiz"
    first, second = await client.post(path), await client.post(path)
    assert (first.status_code, second.status_code) == (202, 202)
    assert first.json() == second.json()
    assert first.json()["status"] == "generating" and first.json()["session_id"]
    assert [g for g, _ in seeded.launcher.started] == ["quiz"]
    assert seeded.launcher.started[0][1] == {"mode": "generate", "quiz_id": first.json()["quiz_id"]}


async def test_ready_quiz_is_returned_with_200(client: httpx.AsyncClient, seeded: Seeded) -> None:
    quiz_id = await ready_quiz(seeded)
    r = await client.post(f"{API}/modules/{seeded.modules[0]}/quiz")
    assert r.status_code == 200 and r.json()["status"] == "ready"
    assert r.json()["quiz_id"] == quiz_id and len(seeded.launcher.started) == 1


async def test_start_quiz_needs_ready_lesson(client: httpx.AsyncClient, seeded: Seeded) -> None:
    r = await client.post(f"{API}/modules/{seeded.modules[1]}/quiz")
    assert (r.status_code, r.json()["error"]["code"]) == (409, "lesson_not_ready")
    r = await client.post(f"{API}/modules/inconnu/quiz")
    assert (r.status_code, r.json()["error"]["code"]) == (404, "module_not_found")
    assert seeded.launcher.started == []


async def test_failed_quiz_session_reads_failed_then_relaunches(
    client: httpx.AsyncClient, seeded: Seeded
) -> None:
    """Session d'écriture échouée hors du port (sortie illisible 3 fois) : lu en échec, sans
    écriture, puis relancé par un nouveau POST."""
    started = (await client.post(f"{API}/modules/{seeded.modules[0]}/quiz")).json()
    await seeded.launcher.end(seeded.user_id, started["session_id"], "failed")
    view = await quiz_view(client, started["quiz_id"])
    assert view["status"] == "failed" and view["failure_reason"] and view["questions"] == []
    again = await client.post(f"{API}/modules/{seeded.modules[0]}/quiz")
    assert again.status_code == 202 and again.json()["quiz_id"] == started["quiz_id"]
    assert again.json()["session_id"] != started["session_id"]
    assert (await quiz_view(client, started["quiz_id"]))["status"] == "generating"


async def test_quiz_hides_answers_before_grading(client: httpx.AsyncClient, seeded: Seeded) -> None:
    quiz_id = await ready_quiz(seeded)
    body = await quiz_view(client, quiz_id)
    assert body["status"] == "ready" and len(body["questions"]) == 10
    hidden = {"correct_index", "expected", "rubric", "explanation", "skill"}
    assert all(not hidden & q.keys() for q in body["questions"])
    assert [q["rank"] for q in body["questions"]] == list(range(1, 11))
    attempt_id = await started_attempt(client, quiz_id)
    r = await client.get(f"{API}/quizzes/{quiz_id}/attempts/{attempt_id}")
    assert r.json() == {
        "id": attempt_id,
        "status": "grading",
        "score": None,
        "passed": None,
        "results": [],
        "followup": None,
    }


async def test_attempt_with_unknown_question_is_422_without_echo(
    client: httpx.AsyncClient, seeded: Seeded
) -> None:
    quiz_id = await ready_quiz(seeded)
    good = await answers(client, quiz_id)
    qcm = next(a for a in good if "choice" in a)
    body = {
        "answers": [
            {"question_id": "question-piegee-secrete", "text": "texte-secret"},
            good[1],
            good[1],
            {**qcm, "choice": 7},
            {"question_id": good[2]["question_id"], "choice": 0},  # choix sur une ouverte
        ]
    }
    r = await client.post(f"{API}/quizzes/{quiz_id}/attempts", json=body)
    assert (r.status_code, r.json()["error"]["code"]) == (422, "invalid_answers")
    assert r.json()["error"]["details"] == {
        "fields": [
            "answers.0.question_id",
            "answers.2.question_id",
            "answers.3.choice",
            "answers.4.choice",
        ]
    }
    assert "secret" not in r.text
    assert await count(seeded, QuizAttempt) == 0


async def test_concurrent_attempts_create_one(client: httpx.AsyncClient, seeded: Seeded) -> None:
    quiz_id = await ready_quiz(seeded)
    body = {"answers": await answers(client, quiz_id)}
    path = f"{API}/quizzes/{quiz_id}/attempts"
    first, second = await asyncio.gather(client.post(path, json=body), client.post(path, json=body))
    assert sorted([first.status_code, second.status_code]) == [202, 409]
    refused = first if first.status_code == 409 else second
    assert refused.json()["error"]["code"] == "attempt_in_progress"
    assert await count(seeded, QuizAttempt, status="grading") == 1


async def test_grading_conflict_in_database_is_409(
    client: httpx.AsyncClient, seeded: Seeded, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F3 : si le contrôle préalable ne voit pas la tentative en cours (autre processus),
    l'index unique partiel refuse le second INSERT : 409 `attempt_in_progress`."""
    quiz_id = await ready_quiz(seeded)
    await started_attempt(client, quiz_id)

    async def nothing(self: AttemptRepository, quiz_ids: object) -> list[QuizAttempt]:
        return []

    monkeypatch.setattr(AttemptRepository, "for_quizzes", nothing)
    r = await post_attempt(client, quiz_id)
    assert (r.status_code, r.json()["error"]["code"]) == (409, "attempt_in_progress")
    assert await count(seeded, QuizAttempt) == 1


async def test_failed_grading_allows_a_new_attempt(
    client: httpx.AsyncClient, seeded: Seeded
) -> None:
    """Notation échouée hors du port (sortie illisible, délai, annulation) : la tentative est lue
    en échec, et une nouvelle est acceptée ; jamais deux tentatives `grading`."""
    quiz_id = await ready_quiz(seeded)
    first = await started_attempt(client, quiz_id)
    session = seeded.launcher.started[-1]
    assert session[1] == {"mode": "grade", "attempt_id": first}
    r = await post_attempt(client, quiz_id)
    assert r.json()["error"]["code"] == "attempt_in_progress"  # session encore ouverte
    async with seeded.rt.session_factory() as db:
        row = await AttemptRepository(db, seeded.user_id).get_fresh(first)
        assert row is not None and row.session_id
        sid = row.session_id
    await seeded.launcher.end(seeded.user_id, sid, "failed")
    shown = await client.get(f"{API}/quizzes/{quiz_id}/attempts/{first}")
    assert shown.json()["status"] == "failed"
    assert (await quiz_view(client, quiz_id))["attempts"][0]["status"] == "failed"
    second = await started_attempt(client, quiz_id)
    assert second != first
    assert await count(seeded, QuizAttempt, status="grading") == 1
    assert await count(seeded, QuizAttempt, status="failed") == 1


async def test_retry_too_soon_after_failure(client: httpx.AsyncClient, seeded: Seeded) -> None:
    quiz_id = await ready_quiz(seeded)
    first_order = [q["id"] for q in (await quiz_view(client, quiz_id))["questions"]]
    attempt_id = await started_attempt(client, quiz_id, right=False)
    assert (await grade(seeded, attempt_id, [0.5] * 7)).score == 35
    r = await post_attempt(client, quiz_id)
    assert (r.status_code, r.json()["error"]["code"]) == (409, "retry_too_soon")
    assert r.json()["error"]["details"] == {"retry_on": "2026-11-19"}
    # Le 19 au matin à Paris (18 à 23 h 30 UTC) : nouvel essai, même quiz mélangé (F27).
    seeded.at(datetime(2026, 11, 18, 23, 30, tzinfo=UTC))
    view = await quiz_view(client, quiz_id)
    order = [q["id"] for q in view["questions"]]
    assert sorted(order) == sorted(first_order) and order != first_order
    choices = [q["choices"] for q in view["questions"] if q["type"] == "qcm"]
    assert any(c.index("Elle normalise") != 0 for c in choices)
    retry = await started_attempt(client, quiz_id, right=True)
    saved = await grade(seeded, retry, PASS_85[:7])
    assert (saved.score, saved.passed) == (85, True)  # bons choix affichés = bons choix rangés


async def test_attempt_out_after_grading(client: httpx.AsyncClient, seeded: Seeded) -> None:
    quiz_id = await ready_quiz(seeded)
    attempt_id = await started_attempt(client, quiz_id, right=False)
    await grade(seeded, attempt_id, FAIL_35)
    body = (await client.get(f"{API}/quizzes/{quiz_id}/attempts/{attempt_id}")).json()
    assert (body["status"], body["score"], body["passed"]) == ("graded", 35, False)
    first = body["results"][0]
    assert first["points"] == 0 and first["correct_answer"] == "Elle normalise"
    assert first["explanation"] and first["feedback"] == ""
    assert body["results"][1]["feedback"] == "Retour de l'Examinateur."
    assert body["followup"]["retry_on"] == "2026-11-19"
    listed = (await client.get(f"{API}/programs/{seeded.program_id}/quizzes")).json()
    assert [(x["quiz_id"], x["status"], x["best_score"], x["retry_on"]) for x in listed] == [
        (quiz_id, "ready", 35, "2026-11-19"),
        (None, None, None, None),
    ]
    assert listed[0]["week_rank"] == 1 and listed[1]["week_rank"] == 2


async def test_quiz_routes_isolate_users(
    client: httpx.AsyncClient, seeded: Seeded, app: FastAPI
) -> None:
    quiz_id = await ready_quiz(seeded)
    attempt_id = await started_attempt(client, quiz_id)
    act_as(app, "un-autre-utilisateur")
    body = {"answers": []}
    for method, path, code in [
        ("post", f"/modules/{seeded.modules[0]}/quiz", "module_not_found"),
        ("get", f"/programs/{seeded.program_id}/quizzes", "program_not_found"),
        ("get", f"/quizzes/{quiz_id}", "quiz_not_found"),
        ("post", f"/quizzes/{quiz_id}/attempts", "quiz_not_found"),
        ("get", f"/quizzes/{quiz_id}/attempts/{attempt_id}", "quiz_not_found"),
    ]:
        kwargs = {"json": body} if path.endswith("attempts") else {}
        r = await client.request(method.upper(), f"{API}{path}", **kwargs)
        assert (r.status_code, r.json()["error"]["code"]) == (404, code), path
    due = (await client.get(f"{API}/flashcards/due")).json()
    assert due["cards"] == [] and due["remaining_due"] == 0
