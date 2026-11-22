from datetime import timedelta
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select

import app.main as main_module
from app.agents.tools.memory_port import AgentWrite
from app.db.base import utcnow
from app.db.models.conversations import ConversationTurn
from app.db.models.lessons import Lesson
from app.features.memory.service.gateway import AgentMemoryGateway
from app.providers.llm.base import ModelChoice, Tier
from app.providers.llm.factory import LlmFactory
from app.providers.llm.fake import FakeLlmProvider
from tests.features.conversations.test_professor import API, question
from tests.features.lessons.test_router import seed
from tests.sessions_support import wait_status


class _Models:
    async def get_model_choice(self, user_id: str, tier: Tier, agent: str | None) -> ModelChoice:
        return ModelChoice(provider="fake", model=tier)


class _Keys:
    async def get_key(self, user_id: str, provider: str) -> str:
        return "fake-key"


@pytest.fixture
def professor_models(monkeypatch: pytest.MonkeyPatch) -> FakeLlmProvider:
    provider = FakeLlmProvider(["Premier éclairage [1].", "Leçon et mémoire [1, 2, 2, 80]."])
    llm = LlmFactory(_Models(), _Keys(), {"fake": provider}, {})
    original = main_module.agent_runtime

    def fake_runtime(*args: Any, **kwargs: Any) -> Any:
        settings, factory, _models, prices, run = args
        return original(settings, factory, llm, prices, run, **kwargs)

    monkeypatch.setattr(main_module, "agent_runtime", fake_runtime)
    return provider


async def test_follow_up_remembers_history_and_resolves_owned_memory_item(
    professor_models: FakeLlmProvider, client: httpx.AsyncClient, app: FastAPI
) -> None:
    lesson = await seed(app)
    memory = AgentMemoryGateway(app.state.memory)
    owned = await memory.write(
        app.state.local_user_id,
        "script",
        "archivist",
        AgentWrite("acquis", "Note vérifiée", "On garde les détails.", "Vu."),
    )
    await memory.write(
        "autre-compte",
        "script",
        "archivist",
        AgentWrite("acquis", "Note étrangère", "Rien à montrer.", "Vu."),
    )
    path = f"{API}/lessons/{lesson.lesson_id}/conversation"
    first = await client.post(f"{path}/messages", json=question("Première question."))
    await wait_status(client, first.json()["session_id"], "completed")
    second = await client.post(f"{path}/messages", json=question("Et pourquoi ?", strong=True))
    await wait_status(client, second.json()["session_id"], "completed")
    turns = (await client.get(path)).json()["turns"]
    assert [turn["answer"] for turn in turns] == [
        "Premier éclairage [1].",
        "Leçon et mémoire [1, 2, 2, 80].",
    ]
    assert turns[1]["sources"] == [
        {"kind": "lesson", "id": lesson.lesson_id, "title": "Module Bases", "excerpt": None},
        {
            "kind": "memory",
            "id": owned.item_id,
            "title": "Note vérifiée",
            "excerpt": "On garde les détails.",
        },
    ]
    assert [model for model, _ in professor_models.built] == ["rapide", "fort"]
    second_prompt = str(professor_models.received[1][-1].content)
    assert "Première question." in second_prompt and "Premier éclairage" in second_prompt
    assert "Note vérifiée" in second_prompt and "Note étrangère" not in second_prompt


@pytest.mark.usefixtures("scripted_professor")
async def test_daily_budget_uses_the_date_of_the_model_call(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    lesson = await seed(app)
    path = f"{API}/lessons/{lesson.lesson_id}/conversation"
    sent = await client.post(f"{path}/messages", json=question())
    sid = sent.json()["session_id"]
    await wait_status(client, sid, "completed")
    async with app.state.session_factory() as db:
        turn = await db.scalar(select(ConversationTurn).where(ConversationTurn.session_id == sid))
        assert turn is not None
        turn.created_at = utcnow() - timedelta(days=1)
        await db.commit()
    usage = (await client.get(path)).json()["usage"]
    assert usage["thread_tokens"] == usage["day_tokens"] > 0


async def test_model_input_is_bounded_in_utf8(
    professor_models: FakeLlmProvider, client: httpx.AsyncClient, app: FastAPI
) -> None:
    lesson = await seed(app)
    async with app.state.session_factory() as db:
        row = await db.get(Lesson, lesson.lesson_id)
        assert row is not None
        row.markdown = "# Leçon\n\n" + "🧪" * 4_000
        await db.commit()
    path = f"{API}/lessons/{lesson.lesson_id}/conversation/messages"
    sent = await client.post(path, json=question("Pourquoi ? " + "🧪" * 1_800))
    assert sent.status_code == 202
    await wait_status(client, sent.json()["session_id"], "completed")
    (messages,) = professor_models.received
    assert any("Pourquoi ?" in str(msg.content) for msg in messages)
    assert sum(len(str(msg.content).encode()) for msg in messages) <= 8800
