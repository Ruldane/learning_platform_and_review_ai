"""La classe relit une leçon publiée et retrouve ses trois camarades au tour suivant."""

from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage

from app.agents.nodes import conversation
from app.agents.runtime.invoke import message_text
from app.agents.runtime.speech import Spoken
from tests import sessions_support
from tests.agents.runtime.runner_helpers import all_events
from tests.features.conversations.test_professor import question
from tests.features.lessons.test_router import seed
from tests.sessions_support import use_test_runtime, wait_status

FIRST = [
    "Tu peux me donner un exemple concret ?",
    "Comment distingues-tu les deux étapes ?",
    "Dans quel cas ton raisonnement atteint-il sa limite ?",
]
SECOND = [
    "Je vois mieux. Par quoi commencer ?",
    "Puis-je reformuler cette distinction ?",
    "Qu'est-ce qui invaliderait notre exemple ?",
]
ROLES = ["beginner", "peer", "advanced"]


@pytest.fixture
def scripted_classroom(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    use_test_runtime(monkeypatch, [*FIRST, *SECOND])
    monkeypatch.setattr(sessions_support, "TIMEOUT", 20.0)
    briefs: list[tuple[str, str]] = []
    speak = conversation.speak

    async def observed(model: BaseChatModel, messages: list[BaseMessage], **options: Any) -> Spoken:
        briefs.append((options["step"], "\n".join(message_text(message) for message in messages)))
        return await speak(model, messages, **options)

    monkeypatch.setattr(conversation, "speak", observed)
    return briefs


async def send(
    client: httpx.AsyncClient, path: str, message: dict[str, object]
) -> tuple[str, dict[str, Any]]:
    started = await client.post(path + "/messages", json=message)
    assert started.status_code == 202, started.text
    session_id: str = started.json()["session_id"]
    try:
        await wait_status(client, session_id, "completed")
    except TimeoutError:
        ended = (await client.get(f"/api/v1/sessions/{session_id}")).json()
        pytest.fail(f"Le tour n'a pas abouti : {ended.get('status')}, {ended.get('error_code')}.")
    thread: dict[str, Any] = (await client.get(path)).json()
    return session_id, thread


async def test_classmates_and_lesson_sources_persist_on_reentry(
    scripted_classroom: list[tuple[str, str]], client: httpx.AsyncClient, app: FastAPI
) -> None:
    lesson = await seed(app)
    base = f"/api/v1/lessons/{lesson.lesson_id}"
    path = base + "/classroom"
    empty = await client.get(path)
    assert empty.status_code == 200 and empty.json() is None

    explanation = question("Ces deux étapes forment une chaîne.")
    session_id, first = await send(client, path, explanation)
    turn = first["turns"][0]
    assert turn["classmates"] == [
        {"role": role, "answer": answer} for role, answer in zip(ROLES, FIRST, strict=True)
    ]
    assert [{source["kind"]: source["id"]} for source in turn["sources"]] == [
        {"lesson": lesson.lesson_id}
    ]
    events = await all_events(app.state.session_factory, app.state.local_user_id, session_id)
    assert [event.agent for event in events if event.type == "agent.message"] == [
        "training_tutor"
    ] * 3
    replay = await client.post(path + "/messages", json=explanation)
    assert replay.status_code == 202 and replay.json() == {"session_id": session_id}
    assert (await client.get(path)).json() == first

    _, reopened = await send(
        client, path, question("La seconde étape emploie le premier résultat.")
    )
    assert reopened["id"] == first["id"]
    assert reopened["turns"][0] == turn
    followup = reopened["turns"][1]
    assert followup["classmates"] == [
        {"role": role, "answer": answer} for role, answer in zip(ROLES, SECOND, strict=True)
    ]
    assert followup["sources"] == turn["sources"]
    assert (await client.get(base + "/conversation")).json() is None
    assert [step for step, _ in scripted_classroom] == [f"classroom_{role}" for role in ROLES] * 2
    assert all("Texte." in prompt for _, prompt in scripted_classroom)
    assert "You are discovering the topic" in scripted_classroom[0][1]
    assert "You have a comparable level" in scripted_classroom[1][1]
    assert "Propose an edge case" in scripted_classroom[2][1]
    assert explanation["question"] in scripted_classroom[3][1]
