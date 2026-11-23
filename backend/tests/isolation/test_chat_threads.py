from datetime import timedelta
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select

from app.db.models.agents import AgentSession
from app.db.models.conversations import ConversationTurn
from app.db.models.skills import UserSkill
from app.db.models.study import Flashcard
from tests.features.brain.conftest import brain_citations  # noqa: F401
from tests.features.brain.test_conversation import add_note, talk
from tests.features.study.conftest import NOW, seed
from tests.features.study.test_training import TRAINING
from tests.features.study.test_training_completion import exercise  # noqa: F401
from tests.sessions_support import act_as, wait_status
from tests.support.conversation_lessons import add_ready_lesson

LIST = "/api/v1/conversations"
BRAIN = "/api/v1/brain"


@pytest.mark.usefixtures("brain_citations")
async def test_brain_keeps_legacy_thread_and_erases_only_chosen_chat(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    note_id, _ = await add_note(app, app.state.local_user_id, "Astres", "Astres et référentiels.")
    first_session = await talk(client, "Astres")
    first = (await client.get(f"{BRAIN}/conversation")).json()
    second = await client.post(f"{BRAIN}/conversations")
    assert second.status_code == 201, second.text
    second_id = second.json()["id"]
    summaries = (await client.get(f"{LIST}/brain")).json()
    assert [item["id"] for item in summaries] == [second_id, first["id"]]
    assert summaries[1]["title"] == "Astres"
    path = f"{LIST}/brain/{first['id']}"
    renamed = await client.patch(path, json={"title": "Céleste et %"})
    assert renamed.json()["title"] == "Céleste et %"
    found = await client.get(f"{LIST}/brain", params={"q": "  CELESTE  "})
    assert [item["id"] for item in found.json()] == [first["id"]]
    literal = await client.get(f"{LIST}/brain", params={"q": "%"})
    assert [item["id"] for item in literal.json()] == [first["id"]]

    get_brain = f"{BRAIN}/conversation"
    params = {"conversation_id": first["id"]}
    assert (await client.get(get_brain, params=params)).json() == first
    assert (await client.delete(f"{path}/messages")).status_code == 204
    assert (await client.get(get_brain, params=params)).json()["turns"] == []
    async with app.state.session_factory() as db:
        assert await db.get(AgentSession, first_session) is None
        assert (await db.scalars(select(ConversationTurn))).all() == []
    assert (await client.get(f"/api/v1/memory/items/{note_id}")).is_success
    assert (await client.delete(path)).status_code == 204
    assert (await client.get(get_brain, params=params)).status_code == 404
    assert (await client.delete(f"{LIST}/brain")).status_code == 204
    assert (await client.get(f"{LIST}/brain")).json() == []


@pytest.mark.parametrize("scope", ["brain", "training"])
async def test_conversation_operations_are_isolated(
    client: httpx.AsyncClient, app: FastAPI, scope: str
) -> None:
    if scope == "brain":
        private = await client.post(f"{BRAIN}/conversations")
        read = f"{BRAIN}/conversation"
        params = {"conversation_id": private.json().get("id")}
    else:
        private = await client.post(TRAINING, json={"new_conversation": True})
        read = f"{TRAINING}/{private.json().get('id')}"
        params = {}
    assert private.is_success, private.text
    path = f"{LIST}/{scope}/{private.json()['id']}"
    owner = app.state.local_user_id
    act_as(app, "autre-compte")
    assert (await client.get(f"{LIST}/{scope}")).json() == []
    assert (await client.get(read, params=params)).status_code == 404
    assert (
        await client.post(
            f"{read}/messages",
            params=params,
            json={"request_id": str(uuid4()), "question": "Question d’un autre compte."},
        )
    ).status_code == 404
    assert (await client.patch(path, json={"title": "Volé"})).status_code == 404
    assert (await client.delete(f"{path}/messages")).status_code == 404
    assert (await client.delete(path)).status_code == 404
    assert (await client.delete(f"{LIST}/{scope}")).status_code == 204
    if scope == "training":
        response = await client.patch(f"{read}/context", json={"action": "mode", "mode": "direct"})
        assert response.status_code == 404
    act_as(app, owner)
    assert (await client.get(read, params=params)).is_success
    assert [item["id"] for item in (await client.get(f"{LIST}/{scope}")).json()] == [
        private.json()["id"]
    ]


async def test_training_selection_and_mode_belong_to_each_conversation(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    first_lesson = await add_ready_lesson(app, app.state.local_user_id, "Algèbre")
    second_lesson = await add_ready_lesson(app, app.state.local_user_id, "Matrices")
    private = await add_ready_lesson(app, "autre-compte", "Autre compte")
    legacy = await client.post(TRAINING, json={"mode": "direct"})
    created = await client.post(
        TRAINING, json={"mode": "socratic", "new_conversation": True, "lesson_ids": [first_lesson]}
    )
    assert created.status_code == 202, created.text
    second = created.json()
    assert second["id"] != legacy.json()["id"]
    assert second["lesson_ids"] == [first_lesson]
    path = f"{TRAINING}/{second['id']}"
    assert (
        await client.patch(path, json={"action": "lessons", "lesson_ids": [private]})
    ).status_code == 404
    updated = await client.patch(path, json={"action": "lessons", "lesson_ids": [second_lesson]})
    assert updated.json()["lesson_ids"] == [second_lesson]
    assert (await client.patch(path, json={"action": "mode", "mode": "feynman"})).json()[
        "mode"
    ] == "feynman"
    old = (await client.get(f"{TRAINING}/{legacy.json()['id']}")).json()
    assert (old["mode"], old["lesson_ids"]) == ("direct", [])
    assert {item["id"] for item in (await client.get(f"{LIST}/training")).json()} == {
        old["id"],
        second["id"],
    }


@pytest.mark.usefixtures("exercise")
async def test_training_wipe_keeps_earned_study_records(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    seeded = await seed(app, recording=False)
    opened = await client.post(TRAINING, json={})
    study_id = opened.json()["id"]
    path = f"{TRAINING}/{study_id}"
    sent = await client.post(
        f"{path}/messages",
        json={
            "request_id": str(uuid4()),
            "question": "Dans le module Bases, normaliser les poids.",
        },
    )
    assert sent.status_code == 202, sent.text
    await wait_status(client, sent.json()["session_id"], "completed")
    seeded.at(NOW + timedelta(minutes=5))
    done = await client.patch(path, json={"action": "finish", "worked_minutes": 5})
    assert done.json()["flashcards_created"] == 1
    context = await client.patch(f"{path}/context", json={"action": "mode", "mode": "direct"})
    assert context.status_code == 200, context.text
    assert context.json()["status"] == "finished" and context.json()["mode"] == "direct"
    resumed = await client.post(
        f"{path}/messages",
        json={"request_id": str(uuid4()), "question": "Je reprends la conversation."},
        headers={"X-Tremplin-Run": "codex"},
    )
    assert resumed.status_code == 202, resumed.text
    sid = resumed.json()["session_id"]
    await wait_status(client, sid, "waiting_user")
    assert (await client.post(f"/api/v1/sessions/{sid}/cancel")).is_success
    assert (await client.delete(f"{LIST}/training")).status_code == 204
    assert (await client.get(path)).status_code == 404
    summary = (await client.get("/api/v1/study-sessions/summary")).json()
    assert summary["streak_days"] == 1 and summary["week_minutes"] == 5
    async with app.state.session_factory() as db:
        card = (await db.scalars(select(Flashcard))).one()
        assert card.source_id == study_id
        assert {
            proof["ref_id"]
            for skill in await db.scalars(select(UserSkill))
            for proof in skill.evidence
        } == {study_id}


async def test_wipe_leaves_all_conversations_when_one_has_an_active_turn(
    client: httpx.AsyncClient,
    app: FastAPI,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = await client.post(f"{BRAIN}/conversations")
    second = await client.post(f"{BRAIN}/conversations")
    sent = await client.post(
        f"{BRAIN}/conversation/messages",
        params={"conversation_id": first.json()["id"]},
        json={"request_id": str(uuid4()), "question": "Un échange en cours."},
        headers={"X-Tremplin-Run": "codex"},
    )
    sid = sent.json()["session_id"]
    await wait_status(client, sid, "waiting_user")
    blocked = await client.delete(f"{LIST}/brain")
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "conversation_busy"
    assert {item["id"] for item in (await client.get(f"{LIST}/brain")).json()} == {
        first.json()["id"],
        second.json()["id"],
    }
    assert (await client.post(f"/api/v1/sessions/{sid}/cancel")).is_success
    # Simule le point entre la transition SQL et l'arrêt du dernier travail du runner.
    with monkeypatch.context() as patch:
        patch.setattr(app.state.runtime.runner, "is_active", lambda session_id: session_id == sid)
        blocked = await client.delete(f"{LIST}/brain")
        assert blocked.status_code == 409
        assert blocked.json()["error"]["code"] == "conversation_busy"
    assert (await client.delete(f"{LIST}/brain")).status_code == 204
