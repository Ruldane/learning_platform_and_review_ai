"""Le fantôme compare des repères, en préservant le détail des réponses."""

import httpx

from app.core.practice import RECENT_PRACTICE
from app.db.models.study import QuizAttempt, QuizQuestion
from app.features.quiz.service.ghost import question_version
from tests.features.quiz.conftest import Seeded
from tests.features.quiz.support import API, PASS_85, answers, grade, ready_quiz, started_attempt


def test_renaming_the_multiple_choice_code_keeps_attempts_on_the_same_version() -> None:
    row = QuizQuestion(
        id="q1",
        quiz_id="quiz",
        user_id="u1",
        rank=1,
        type="qcm",
        prompt="Which query filters the rows?",
        choices=["SELECT", "WHERE", "ORDER BY"],
        correct_index=1,
        skill="SQL",
    )
    legacy = question_version([row])
    row.type = "mcq"
    assert question_version([row]) == legacy


async def test_ghost_shows_recorded_metrics_without_replaying_answers(
    seeded: Seeded, client: httpx.AsyncClient
) -> None:
    quiz_id = await ready_quiz(seeded)
    legacy = await started_attempt(client, quiz_id)
    await grade(seeded, legacy, PASS_85)
    async with seeded.rt.session_factory() as db:
        old = await db.get(QuizAttempt, legacy)
        assert old is not None
        old.question_version = None
        await db.commit()

    sent = await client.post(
        f"{API}/quizzes/{quiz_id}/attempts",
        json={"answers": await answers(client, quiz_id), "elapsed_ms": 67000},
    )
    assert sent.status_code == 202
    latest = sent.json()["attempt_id"]
    await grade(seeded, latest, PASS_85)

    response = await client.get(f"{API}/quizzes/{quiz_id}/ghost")
    assert response.status_code == 200
    recent, old_summary = response.json()
    assert recent["id"] == latest
    assert recent["elapsed_ms"] == 67000
    assert recent["errors"] == 2
    assert recent["progress"] == 10
    assert recent["total"] == 10
    assert recent["version"] == "same"
    assert old_summary["id"] == legacy
    assert old_summary["elapsed_ms"] is None
    assert old_summary["version"] == "unknown"
    assert old_summary["score_percent"] == 85
    assert "answers" not in response.text
    assert "Ma réponse" not in response.text
    assert "Retour de l'Examinateur" not in response.text

    await fill_recent_window(seeded, quiz_id, latest)
    assert legacy not in (await client.get(f"{API}/quizzes/{quiz_id}/ghost")).text
    linked = await client.get(f"{API}/quizzes/{quiz_id}/ghost", params={"attempt_id": legacy})
    assert linked.status_code == 200
    assert linked.json()[-1]["id"] == legacy


async def fill_recent_window(seeded: Seeded, quiz_id: str, latest: str) -> None:
    async with seeded.rt.session_factory() as db:
        current = await db.get(QuizAttempt, latest)
        assert current is not None
        db.add_all(
            [
                QuizAttempt(
                    user_id=seeded.user_id,
                    quiz_id=quiz_id,
                    status="graded",
                    question_version=current.question_version,
                )
                for _ in range(RECENT_PRACTICE)
            ]
        )
        await db.commit()
