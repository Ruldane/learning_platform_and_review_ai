"""La route du professeur utilise les vrais fils, sessions et événements."""

from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select

from app.db.models.agents import AgentSession
from app.db.models.lessons import Lesson
from tests.agents.runtime.runner_helpers import all_events
from tests.features.lessons.test_router import seed
from tests.sessions_support import wait_status

API = "/api/v1"


def question(text: str = "Peux-tu préciser ce passage ?", **extra: object) -> dict[str, object]:
    return {"request_id": str(uuid4()), "question": text, **extra}


async def test_read_without_a_turn_returns_null(client: httpx.AsyncClient, app: FastAPI) -> None:
    lesson = await seed(app)
    path = f"{API}/lessons/{lesson.lesson_id}/conversation"
    for _ in range(2):
        read = await client.get(path)
        assert read.status_code == 200
        assert read.json() is None


@pytest.mark.usefixtures("scripted_professor")
async def test_persists_answer_and_resolves_citations(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    lesson = await seed(app)
    path = f"{API}/lessons/{lesson.lesson_id}/conversation"
    payload = question(passage="Texte.")
    sent = await client.post(f"{path}/messages", json=payload)
    assert sent.status_code == 202, sent.text
    sid = sent.json()["session_id"]
    await wait_status(client, sid, "completed")
    read = (await client.get(path)).json()
    assert read["lesson_id"] == lesson.lesson_id
    (turn,) = read["turns"]
    assert turn["request_id"] == payload["request_id"] and turn["session_id"] == sid
    assert turn["question"] == payload["question"] and turn["passage"] == "Texte."
    assert turn["answer"].startswith("Voici l'explication") and turn["status"] == "completed"
    assert turn["sources"] == [
        {"kind": "lesson", "id": lesson.lesson_id, "title": "Module Bases", "excerpt": "Texte."}
    ]
    events = await all_events(app.state.session_factory, app.state.local_user_id, sid)
    assert {"agent.token", "agent.message"} <= {event.type for event in events}
    replay = await client.post(f"{path}/messages", json=payload)
    assert replay.status_code == 202 and replay.json() == sent.json()
    assert (await client.get(path)).json() == read


async def test_wrong_or_unpublished_passage_never_starts_a_session(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    lesson = await seed(app)
    body = question(passage="Passage privé jamais publié.")
    for lesson_id, code in (
        (lesson.lesson_id, "conversation_passage_stale"),
        (lesson.pending_id, "lesson_not_ready"),
    ):
        path = f"{API}/lessons/{lesson_id}/conversation/messages"
        refused = await client.post(path, json=body)
        assert refused.status_code == 409
        assert refused.json()["error"]["code"] == code
        assert "privé" not in refused.text
    async with app.state.session_factory() as db:
        assert (await db.scalars(select(AgentSession))).all() == []


@pytest.mark.usefixtures("scripted_professor")
async def test_passage_matches_rendered_markdown(client: httpx.AsyncClient, app: FastAPI) -> None:
    lesson = await seed(app)
    async with app.state.session_factory() as db:
        row = await db.get(Lesson, lesson.lesson_id)
        assert row is not None
        row.markdown = "# Module Bases\n\nUn **fragment** et [un lien](https://example.invalid)."
        await db.commit()
    path = f"{API}/lessons/{lesson.lesson_id}/conversation"
    payload = question(passage="Un fragment\n et un lien.")
    response = await client.post(f"{path}/messages", json=payload)
    assert response.status_code == 202, response.text
    await wait_status(client, response.json()["session_id"], "completed")
    (turn,) = (await client.get(path)).json()["turns"]
    assert turn["passage"] == "Un fragment et un lien."


async def test_selects_the_named_occurrence_in_the_visible_lesson(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    lesson = await seed(app)
    async with app.state.session_factory() as db:
        row = await db.get(Lesson, lesson.lesson_id)
        assert row is not None
        row.markdown = (
            "# Un passage\n\nUn passage\n\n" + "a " * 5000 + "\n\nEnfin Un passage choisi."
        )
        await db.commit()
    path = f"{API}/lessons/{lesson.lesson_id}/conversation"
    missing = await client.post(f"{path}/messages", json=question(passage="Un passage"))
    assert missing.status_code == 409
    assert missing.json()["error"]["code"] == "conversation_passage_ambiguous"
    stale = await client.post(
        f"{path}/messages", json=question(passage="Un passage", passage_occurrence=2)
    )
    assert (
        stale.status_code == 409 and stale.json()["error"]["code"] == "conversation_passage_stale"
    )
    sent = await client.post(
        f"{path}/messages",
        json=question(passage="Un passage", passage_occurrence=1),
        headers={"X-Tremplin-Run": "codex"},
    )
    assert sent.status_code == 202, sent.text
    sid = sent.json()["session_id"]
    await wait_status(client, sid, "waiting_user")
    async with app.state.session_factory() as db:
        session = await db.get(AgentSession, sid)
        assert session is not None and session.pending_interrupt
        assert any(
            "Enfin Un passage choisi." in message["content"]
            for message in session.pending_interrupt["brief"]["messages"]
        )
    (turn,) = (await client.get(path)).json()["turns"]
    assert turn["passage_occurrence"] == 1


async def test_lesson_graph_cannot_be_launched_without_its_route(client: httpx.AsyncClient) -> None:
    refused = await client.post(f"{API}/sessions", json={"graph": "conversation", "input": {}})
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "graph_has_route"


@pytest.mark.parametrize(
    "fields",
    [
        {"request_id": "secret-invalide"},
        {"question": " "},
        {"question": "x" * 2001},
        {"passage": "x" * 1001},
        {"strong": "oui"},
    ],
)
async def test_rejects_invalid_or_oversized_fields(
    client: httpx.AsyncClient, app: FastAPI, fields: dict[str, object]
) -> None:
    lesson = await seed(app)
    path = f"{API}/lessons/{lesson.lesson_id}/conversation/messages"
    refused = await client.post(path, json=question() | fields)
    assert refused.status_code == 422
    assert "secret-invalide" not in refused.text and "x" * 100 not in refused.text
