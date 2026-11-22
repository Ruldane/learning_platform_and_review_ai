"""Les corrections restent privées et l’exercice appartient au compte de la leçon."""

import httpx
from fastapi import FastAPI

from app.db.models.accounts import User
from app.db.models.lesson_hunt import LessonHunt
from tests.e2e.lesson_hunt import EDITS, SOURCE
from tests.features.lessons.test_router import seed
from tests.sessions_support import act_as


async def test_exercise_does_not_reveal_answers_or_cross_accounts(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    lesson = await seed(app)
    owner = app.state.local_user_id
    other = "autre-compte-chasse"
    async with app.state.session_factory() as db:
        row = LessonHunt(
            user_id=owner,
            lesson_id=lesson.lesson_id,
            title="Module Bases",
            source=SOURCE,
            stage="ready",
            session_id="session-exercice-synthetique",
            exercise="Un tuple est modifiable. Un ensemble conserve les doublons.",
            errors={"edits": EDITS},
        )
        db.add_all([row, User(id=other, user_id=other)])
        await db.commit()
    path = f"/api/v1/lesson-hunts/{row.id}"
    own = await client.get(path)
    assert own.status_code == 200
    assert own.json()["corrections"] is None
    assert all(edit["explanation"] not in own.text for edit in EDITS)

    act_as(app, other)
    assert (await client.get(path)).status_code == 404
    foreign = await client.post("/api/v1/lesson-hunts", json={"lesson_id": lesson.lesson_id})
    assert foreign.status_code == 404
