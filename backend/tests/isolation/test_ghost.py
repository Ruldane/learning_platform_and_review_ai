"""Les deux historiques de défi sont privés."""

import httpx
from fastapi import FastAPI

from app.db.models.accounts import User
from app.db.models.ide import IdeRun, IdeSession
from tests.features.ide.support import new_session
from tests.features.quiz.conftest import seed
from tests.features.quiz.support import PASS_85, grade, ready_quiz, started_attempt
from tests.sessions_support import act_as


async def test_ghost_stays_in_the_account(app: FastAPI, client: httpx.AsyncClient) -> None:
    seeded = await seed(app)
    quiz = await ready_quiz(seeded)
    await grade(seeded, await started_attempt(client, quiz), PASS_85)
    session = await new_session(client, title="Exercice isolé")
    paths = [
        f"/api/v1/quizzes/{quiz}/ghost",
        f"/api/v1/ide/sessions/{session['id']}/ghost",
    ]
    other = "autre-compte-fantome"
    async with app.state.session_factory() as db:
        db.add(User(id=other, user_id=other))
        # Une séance étrangère pointant sur le même identifiant d’exercice est ignorée.
        foreign = IdeSession(user_id=other, exercise_id=session["exercise_id"], title="Étranger")
        db.add(foreign)
        await db.flush()
        run = IdeRun(user_id=other, session_id=foreign.id, kind="check", status="done", exit_code=0)
        db.add(run)
        await db.commit()
        foreign_run_id = run.id
    res = await client.get(paths[0])
    assert res.status_code == 200 and len(res.json()) == 1
    res = await client.get(paths[1], params={"run_id": foreign_run_id})
    assert res.status_code == 200 and res.json() == []
    act_as(app, other)
    for path in paths:
        assert (await client.get(path)).status_code == 404
