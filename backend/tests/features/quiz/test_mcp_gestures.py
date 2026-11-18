"""Gestes de January (10.R, I1) : répondre à un quiz et noter une fiche sont ses gestes, jamais
faits à sa place par Claude (MCP). Sous identité MCP la route refuse (403 `mcp_gesture_forbidden`) :
aucune tentative, aucune fiche touchée, aucune compétence ni preuve."""

import httpx
from sqlalchemy import func, select

from app.db.models.skills import UserSkill
from app.db.models.study import Flashcard, QuizAttempt
from tests.features.ide.mcp_support import acting_as_claude
from tests.features.quiz.conftest import Seeded
from tests.features.quiz.support import API, answers, ready_quiz
from tests.features.quiz.test_cards import TODAY, _cards


async def _count(s: Seeded, model: type) -> int:
    async with s.rt.session_factory() as db:
        return int((await db.execute(select(func.count()).select_from(model))).scalar_one())


async def test_claude_cannot_answer_a_quiz(client: httpx.AsyncClient, seeded: Seeded) -> None:
    quiz_id = await ready_quiz(seeded)
    body = {"answers": await answers(client, quiz_id)}
    launched = len(seeded.launcher.started)  # la préparation du quiz, avant le refus
    with acting_as_claude(seeded.user_id):
        refused = await client.post(f"{API}/quizzes/{quiz_id}/attempts", json=body)
    assert refused.status_code == 403
    assert refused.json()["error"]["code"] == "mcp_gesture_forbidden"
    assert await _count(seeded, QuizAttempt) == 0
    assert await _count(seeded, UserSkill) == 0
    assert len(seeded.launcher.started) == launched  # aucune notation lancée
    again = await client.post(f"{API}/quizzes/{quiz_id}/attempts", json=body)  # January, elle, peut
    assert again.status_code == 202, again.text


async def test_claude_cannot_review_a_card(client: httpx.AsyncClient, seeded: Seeded) -> None:
    [card_id] = await _cards(seeded, 1)
    with acting_as_claude(seeded.user_id):
        refused = await client.post(f"{API}/flashcards/{card_id}/review", json={"result": "ok"})
    assert refused.status_code == 403
    assert refused.json()["error"]["code"] == "mcp_gesture_forbidden"
    async with seeded.rt.session_factory() as db:
        card = await db.get(Flashcard, card_id)
        assert card is not None and card.step == 2 and card.last_reviewed_on is None
        assert card.due_date == TODAY
    done = await client.post(f"{API}/flashcards/{card_id}/review", json={"result": "ok"})
    assert done.status_code == 200, done.text


async def test_quiz_gestures_are_not_tools(client: httpx.AsyncClient, app) -> None:  # type: ignore[no-untyped-def]
    names = {tool.name for tool in app.state.mcp_registry.all()}
    assert {"quiz_submit_attempt", "quiz_review_card"}.isdisjoint(names)
    assert {"quiz_get_attempt", "quiz_list_due_cards", "quiz_write_quiz"} <= names
