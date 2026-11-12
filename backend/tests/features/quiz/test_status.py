"""Statuts lus des quiz (D101 n° 4, D97 n° 9) : la liste lit les sessions ouvertes une seule fois,
AVANT les lignes ; un quiz `generating` sans session est lu en échec ; une tentative dont la
session est terminée sans notes n'empêche pas un nouvel essai."""

from typing import cast

import httpx
from sqlalchemy import Engine, event, update

from app.db.models.lessons import Lesson
from app.db.models.study import QuizAttempt
from app.features.quiz.repository import AttemptRepository, QuizRepository
from tests.features.quiz.conftest import Seeded
from tests.features.quiz.support import (
    API,
    count,
    post_attempt,
    quiz_view,
    ready_quiz,
    started_attempt,
)


async def _ready_lesson(s: Seeded, module_id: str) -> None:
    async with s.rt.session_factory() as db:
        await db.execute(
            update(Lesson)
            .where(Lesson.module_id == module_id)
            .values(status="ready", markdown="# Module\n\nTexte.")
        )
        await db.commit()


async def test_list_reads_open_sessions_once_before_the_quizzes(
    client: httpx.AsyncClient, seeded: Seeded
) -> None:
    """D97 n° 9 : sessions, PUIS lignes ; une requête de sessions pour tous les quiz (pas une
    par quiz)."""
    await _ready_lesson(seeded, seeded.modules[1])
    await ready_quiz(seeded, 0)
    await ready_quiz(seeded, 1)
    statements: list[str] = []

    def record(conn: object, cursor: object, statement: str, *rest: object) -> None:
        statements.append(statement)

    async with seeded.rt.session_factory() as db:
        engine = cast(Engine, db.get_bind())
    event.listen(engine, "before_cursor_execute", record)
    try:
        r = await client.get(f"{API}/programs/{seeded.program_id}/quizzes")
    finally:
        event.remove(engine, "before_cursor_execute", record)
    assert r.status_code == 200
    assert [row["status"] for row in r.json() if row["quiz_id"]] == ["ready", "ready"]
    sessions = [i for i, sql in enumerate(statements) if "FROM sessions" in sql]
    quizzes = [i for i, sql in enumerate(statements) if "FROM quizzes" in sql]
    assert len(sessions) == 1 and quizzes
    assert sessions[0] < quizzes[0]


async def test_generating_quiz_without_session_reads_failed_then_relaunches(
    client: httpx.AsyncClient, seeded: Seeded
) -> None:
    """Arrêt entre le commit de la ligne et le rangement de la session : la lecture montre
    l'échec (« Relancer » possible), sans écrire ; un POST relance."""
    module_id = seeded.modules[0]
    async with seeded.rt.session_factory() as db:
        quiz = await QuizRepository(db, seeded.user_id).add(
            module_id=module_id, program_id=seeded.program_id, title="Module"
        )
        quiz_id = quiz.id
        await db.commit()
    view = await quiz_view(client, quiz_id)
    assert view["status"] == "failed" and view["failure_reason"] and view["questions"] == []
    listed = (await client.get(f"{API}/programs/{seeded.program_id}/quizzes")).json()
    assert [row["status"] for row in listed if row["quiz_id"] == quiz_id] == ["failed"]
    async with seeded.rt.session_factory() as db:
        row = await QuizRepository(db, seeded.user_id).get_fresh(quiz_id)
        assert row is not None and row.status == "generating"  # rien n'a été écrit
    again = await client.post(f"{API}/modules/{module_id}/quiz")
    assert again.status_code == 202 and again.json()["quiz_id"] == quiz_id
    assert (
        again.json()["session_id"] and (await quiz_view(client, quiz_id))["status"] == "generating"
    )


async def test_grading_completed_without_grades_allows_a_new_attempt(
    client: httpx.AsyncClient, seeded: Seeded
) -> None:
    """Session de notation `completed` sans notes (le port n'a rien écrit) : tentative lue en
    échec, nouvel essai accepté, jamais deux tentatives `grading`."""
    quiz_id = await ready_quiz(seeded)
    first = await started_attempt(client, quiz_id)
    async with seeded.rt.session_factory() as db:
        row = await AttemptRepository(db, seeded.user_id).get_fresh(first)
        assert row is not None and row.session_id
        sid = row.session_id
    await seeded.launcher.end(seeded.user_id, sid, "completed")
    assert (await quiz_view(client, quiz_id))["attempts"][0]["status"] == "failed"
    second = await post_attempt(client, quiz_id)
    assert second.status_code == 202, second.text
    assert second.json()["attempt_id"] != first
    assert await count(seeded, QuizAttempt, status="grading") == 1
    assert await count(seeded, QuizAttempt, status="failed") == 1
