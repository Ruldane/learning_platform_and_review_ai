from asyncio import gather

import httpx
from fastapi import FastAPI
from sqlalchemy import select

from app.db.models.agents import AgentSession
from app.db.models.study import StudySession
from tests.features.study.conftest import seed

STUDY = "/api/v1/study-sessions"
TRAINING = f"{STUDY}/training"


async def test_training_starts_once_without_a_lesson_or_agent(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    assert (await client.get(f"{TRAINING}/open")).json() is None
    first, second = await gather(
        client.post(TRAINING, json={"mode": "direct"}),
        client.post(TRAINING, json={"mode": "direct"}),
    )
    assert sorted((first.status_code, second.status_code)) == [200, 202]
    assert first.json() == second.json()
    session = first.json()
    assert session["mode"] == "direct" and session["status"] == "open"
    assert session["greeting"] and session["conversation"]["turns"] == []
    assert session["conversation"]["id"] == session["id"]
    assert (await client.get(f"{TRAINING}/open")).json() == session
    assert (await client.get(f"{TRAINING}/{session['id']}")).json() == session
    async with app.state.session_factory() as db:
        row = (await db.scalars(select(StudySession))).one()
        assert row.kind == "training"
        assert row.lesson_id is None and row.module_id is None and row.program_id is None
        assert (await db.scalars(select(AgentSession))).all() == []


async def test_training_and_guided_share_the_open_session_slot(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    seeded = await seed(app)
    guided = await client.post(STUDY, json={"lesson_id": seeded.lessons[0]})
    assert guided.status_code == 202
    blocked = await client.post(TRAINING, json={})
    assert blocked.status_code == 409 and blocked.json()["error"]["code"] == "study_already_open"
    guided_id = guided.json()["study_session_id"]
    assert (await client.patch(f"{STUDY}/{guided_id}", json={"action": "cancel"})).is_success
    opened = await client.post(TRAINING, json={})
    assert opened.is_success, opened.text
    rejected = await client.post(STUDY, json={"lesson_id": seeded.lessons[0]})
    assert rejected.status_code == 409 and rejected.json()["error"]["code"] == "study_already_open"
    assert rejected.json()["error"]["details"] == {
        "study_session_id": opened.json()["id"],
        "kind": "training",
    }
    assert (await client.get(f"{TRAINING}/open")).json()["id"] == opened.json()["id"]
    assert (await client.get(f"{STUDY}/summary")).json()["open_session_id"] is None
    assert (await client.get(f"{STUDY}/{opened.json()['id']}")).status_code == 404
