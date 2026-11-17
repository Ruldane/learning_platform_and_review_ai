"""Quiz écrit en direct (10.W) : `POST /quizzes`, `POST /quizzes/{id}/questions` et les `PATCH`
rangent les questions de January ou de Claude comme le port de l'Examinateur, sans agent ni appel
au modèle."""

from typing import Any

import httpx
from fastapi import FastAPI
from sqlalchemy import select

from app.db.models.study import Quiz, QuizAttempt, QuizQuestion
from tests.sessions_support import act_as
from tests.support.direct import API, OTHER, Seed, assert_no_agent

SECRET = "SECRET-DU-QUIZ"
QCM: dict[str, Any] = {
    "type": "qcm",
    "prompt": "Que renvoie len([1, 2, 3]) ?",
    "choices": ["2", "3", "4"],
    "correct_index": 1,
    "explanation": "Trois éléments.",
    "skill": "PANDAS",
}
OPEN: dict[str, Any] = {
    "type": "short",
    "prompt": "Pourquoi indexer un DataFrame ?",
    "expected": "Pour accéder vite aux lignes.",
    "rubric": ["Parle de l'accès rapide"],
    "skill": "numpy",
}


async def questions_of(app: FastAPI, quiz_id: str) -> list[QuizQuestion]:
    async with app.state.session_factory() as db:
        stmt = (
            select(QuizQuestion).where(QuizQuestion.quiz_id == quiz_id).order_by(QuizQuestion.rank)
        )
        return list((await db.execute(stmt)).scalars())


async def write(client: httpx.AsyncClient, drafted: Seed, **over: Any) -> httpx.Response:
    body = {"module_id": drafted.modules[0], "title": "Quiz des bases", "questions": [QCM, OPEN]}
    return await client.post(f"{API}/quizzes", json=body | over)


async def test_write_quiz_is_ready_and_hides_the_answers(
    client: httpx.AsyncClient,
    app: FastAPI,
    drafted: Seed,
) -> None:
    r = await write(client, drafted)

    assert r.status_code == 201, r.text
    quiz = r.json()
    assert (quiz["status"], quiz["title"], quiz["module_id"]) == (
        "ready",
        "Quiz des bases",
        drafted.modules[0],
    )
    assert [q["type"] for q in quiz["questions"]] == ["qcm", "short"] and quiz["attempts"] == []
    assert "correct_index" not in r.text and "expected" not in r.text  # jamais avant une note
    assert (await client.get(f"{API}/quizzes/{quiz['id']}")).json()["status"] == "ready"
    rows = await questions_of(app, quiz["id"])
    assert [row.rank for row in rows] == [1, 2] and rows[0].correct_index == 1
    assert rows[0].skill == "pandas"  # la compétence du module, pas celle écrite
    summary = (await client.get(f"{API}/programs/{drafted.program_id}/quizzes")).json()
    assert summary[0]["quiz_id"] == quiz["id"] and summary[0]["status"] == "ready"
    await assert_no_agent(app)


async def test_second_quiz_for_a_module_is_refused(
    client: httpx.AsyncClient,
    drafted: Seed,
) -> None:
    assert (await write(client, drafted)).status_code == 201

    again = await write(client, drafted)

    assert (again.status_code, again.json()["error"]["code"]) == (409, "quiz_exists")


async def test_add_and_patch_questions_and_title(
    client: httpx.AsyncClient,
    app: FastAPI,
    drafted: Seed,
) -> None:
    quiz_id = (await write(client, drafted)).json()["id"]

    added = await client.post(
        f"{API}/quizzes/{quiz_id}/questions", json=OPEN | {"prompt": "Une autre question ?"}
    )
    assert added.status_code == 201, added.text
    assert len(added.json()["questions"]) == 3
    [first, _, third] = await questions_of(app, quiz_id)
    assert third.rank == 3

    patched = await client.patch(
        f"{API}/quizzes/{quiz_id}/questions/{first.id}",
        json={"prompt": "Que vaut len([]) ?", "correct_index": 0},
    )
    assert patched.status_code == 200, patched.text
    assert (await questions_of(app, quiz_id))[0].prompt == "Que vaut len([]) ?"
    retitled = await client.patch(f"{API}/quizzes/{quiz_id}", json={"title": "Nouveau titre"})
    assert retitled.json()["title"] == "Nouveau titre"
    await assert_no_agent(app)


async def test_a_quiz_with_attempts_keeps_its_questions_and_is_capped_at_twelve(
    client: httpx.AsyncClient,
    app: FastAPI,
    drafted: Seed,
) -> None:
    quiz_id = (await write(client, drafted, questions=[OPEN] * 12)).json()["id"]
    full = await client.post(f"{API}/quizzes/{quiz_id}/questions", json=OPEN)
    assert (full.status_code, full.json()["error"]["code"]) == (409, "quiz_full")
    async with app.state.session_factory() as db:
        db.add(QuizAttempt(user_id=drafted.user_id, quiz_id=quiz_id, status="graded", score=50))
        await db.commit()
    first = (await questions_of(app, quiz_id))[0]

    added = await client.post(f"{API}/quizzes/{quiz_id}/questions", json=OPEN)
    patched = await client.patch(
        f"{API}/quizzes/{quiz_id}/questions/{first.id}", json={"prompt": "Autre question ?"}
    )

    for r in (added, patched):
        assert (r.status_code, r.json()["error"]["code"]) == (409, "quiz_has_attempts")


async def test_invalid_questions_are_422_without_echo(
    client: httpx.AsyncClient,
    drafted: Seed,
) -> None:
    bad = [
        QCM | {"choices": [SECRET, SECRET, "b"]},  # choix identiques
        QCM | {"correct_index": 7, "prompt": SECRET * 5},
        QCM | {"choices": [SECRET, "a"]},  # trop peu de choix
        OPEN | {"rubric": [], "prompt": SECRET * 5},
        OPEN | {"type": "code", "prompt": SECRET * 5},  # sans extrait
        OPEN | {"choices": [SECRET, "x", "y"], "prompt": SECRET * 5},
        OPEN | {"prompt": SECRET * 200},
    ]
    for question in bad:
        r = await write(client, drafted, questions=[question])
        assert r.status_code == 422 and SECRET not in r.text, question
    assert (await write(client, drafted, questions=[])).status_code == 422
    quiz_id = (await write(client, drafted)).json()["id"]
    r = await client.post(f"{API}/quizzes/{quiz_id}/questions", json=QCM | {"correct_index": 9})
    assert r.status_code == 422
    r = await client.patch(
        f"{API}/quizzes/{quiz_id}/questions/inconnue", json={"choices": [SECRET]}
    )
    assert SECRET not in r.text


async def test_quiz_write_is_isolated_between_users(
    client: httpx.AsyncClient,
    app: FastAPI,
    drafted: Seed,
) -> None:
    quiz_id = (await write(client, drafted)).json()["id"]
    first = (await questions_of(app, quiz_id))[0]
    act_as(app, OTHER)

    results = [
        await write(client, drafted, module_id=drafted.modules[1]),
        await client.patch(f"{API}/quizzes/{quiz_id}", json={"title": "Pris"}),
        await client.post(f"{API}/quizzes/{quiz_id}/questions", json=OPEN),
        await client.patch(
            f"{API}/quizzes/{quiz_id}/questions/{first.id}", json={"prompt": "Pris ?"}
        ),
    ]

    assert [r.status_code for r in results] == [404, 404, 404, 404]
    assert [r.json()["error"]["code"] for r in results] == [
        "module_not_found",
        "quiz_not_found",
        "quiz_not_found",
        "quiz_not_found",
    ]
    async with app.state.session_factory() as db:
        assert (await db.execute(select(Quiz))).scalars().all()[0].title == "Quiz des bases"
