import asyncio

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select

from app.db.models.agents import AgentSession, LlmCall
from app.db.models.lessons import Lesson
from app.features.conversations.store import AgentConversationStore
from tests.agents.runtime.runner_helpers import wait_idle
from tests.features.conversations.test_professor import API, question
from tests.features.lessons.test_router import seed
from tests.mcp.adapter_support import call
from tests.mcp.support import Mcp
from tests.sessions_support import wait_status
from tests.support.direct import claude  # noqa: F401


async def test_concurrent_duplicate_reserves_exactly_one_turn(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    lesson = await seed(app)
    path = f"{API}/lessons/{lesson.lesson_id}/conversation"
    data = question()
    headers = {"X-Tremplin-Run": "codex"}
    left, right = await asyncio.gather(
        client.post(f"{path}/messages", json=data, headers=headers),
        client.post(f"{path}/messages", json=data, headers=headers),
    )
    assert left.status_code == right.status_code == 202
    assert left.json() == right.json()
    sid = left.json()["session_id"]
    await wait_status(client, sid, "waiting_user")
    busy = await client.post(f"{path}/messages", json=question(), headers=headers)
    assert (busy.status_code, busy.json()["error"]["code"]) == (409, "conversation_busy")
    changed = await client.post(f"{path}/messages", json=data | {"strong": True}, headers=headers)
    assert (changed.status_code, changed.json()["error"]["code"]) == (
        409,
        "conversation_request_conflict",
    )
    assert [t["session_id"] for t in (await client.get(path)).json()["turns"]] == [sid]


async def test_codex_plays_professor_through_the_same_route(
    client: httpx.AsyncClient,
    app: FastAPI,
    claude: Mcp,  # noqa: F811
) -> None:
    lesson = await seed(app)
    app.state.runtime.runner.launch_quota.limit = 1
    token = await claude.token(("sessions", "conversations"), "write")
    arguments = {
        "launch": "conversations_ask_professor",
        "played_by": "codex",
        "arguments": {"lesson_id": lesson.lesson_id, **question(passage="Texte.")},
    }
    started, refused = await call(
        claude,
        token,
        "agents_play_start",
        arguments,
    )
    assert not refused, started
    sid = started["data"]["session_id"]
    replayed, refused = await call(claude, token, "agents_play_start", arguments)
    assert not refused and replayed["data"]["session_id"] == sid, replayed
    await wait_idle(app.state.runtime.runner, sid)
    brief, refused = await call(claude, token, "agents_play_brief", {"session_id": sid})
    assert not refused, brief
    assert brief["data"]["agent"] == "lesson_professor"
    submit = {"session_id": sid, "step_id": brief["data"]["step_id"], "response": "Réponse [1]."}
    submitted, refused = await call(claude, token, "agents_play_submit", submit)
    assert not refused, submitted
    await wait_status(client, sid, "completed")
    _, duplicate = await call(claude, token, "agents_play_submit", submit)
    assert duplicate
    read, refused = await call(
        claude, token, "conversations_read_professor", {"lesson_id": lesson.lesson_id}
    )
    assert not refused, read
    (turn,) = read["data"]["turns"]
    assert turn["session_id"] == sid and "Réponse [1]." in turn["answer"]
    assert turn["sources"][0]["id"] == lesson.lesson_id
    over_limit, refused = await call(
        claude,
        token,
        "agents_play_start",
        arguments | {"arguments": {"lesson_id": lesson.lesson_id, **question()}},
    )
    assert refused and over_limit["data"]["error"]["code"] == "mcp_graph_quota"


async def test_passage_rechecked_when_played_model_resumes(
    client: httpx.AsyncClient,
    app: FastAPI,
    claude: Mcp,  # noqa: F811
) -> None:
    lesson = await seed(app)
    path = f"{API}/lessons/{lesson.lesson_id}/conversation"
    started = await client.post(
        f"{path}/messages", json=question(passage="Texte."), headers={"X-Tremplin-Run": "codex"}
    )
    sid = started.json()["session_id"]
    await wait_status(client, sid, "waiting_user")
    token = await claude.token(("sessions", "conversations"), "write")
    brief, refused = await call(claude, token, "agents_play_brief", {"session_id": sid})
    assert not refused, brief
    async with app.state.session_factory() as db:
        row = await db.get(Lesson, lesson.lesson_id)
        assert row is not None
        row.markdown = "# Module Bases\n\nNouveau passage."
        await db.commit()
    submitted, refused = await call(
        claude,
        token,
        "agents_play_submit",
        {"session_id": sid, "step_id": brief["data"]["step_id"], "response": "Ancien extrait [1]."},
    )
    assert not refused, submitted
    session = await wait_status(client, sid, "failed")
    assert session["error"]["code"] == "conversation_passage_stale"
    (turn,) = (await client.get(path)).json()["turns"]
    assert turn["answer"] is None and turn["sources"] == []


@pytest.mark.usefixtures("scripted_professor")
async def test_resume_after_reply_does_not_repeat_model_call(
    client: httpx.AsyncClient, app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    lesson = await seed(app)
    path = f"{API}/lessons/{lesson.lesson_id}/conversation"
    save_reached = asyncio.Event()
    can_save = asyncio.Event()
    original = AgentConversationStore.save_reply

    async def delay_save(self: AgentConversationStore, *args: object, **kwargs: object) -> None:
        save_reached.set()
        await can_save.wait()
        await original(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(AgentConversationStore, "save_reply", delay_save)
    sent = await client.post(f"{path}/messages", json=question())
    sid = sent.json()["session_id"]
    async with asyncio.timeout(10):
        await save_reached.wait()
    assert (await client.post(f"{API}/sessions/{sid}/pause")).is_success
    can_save.set()
    assert (await client.post(f"{API}/sessions/{sid}/resume", json={})).is_success
    await wait_status(client, sid, "completed")
    (turn,) = (await client.get(path)).json()["turns"]
    assert turn["status"] == "completed" and turn["answer"].startswith("Voici l'explication")


@pytest.mark.usefixtures("scripted_professor")
@pytest.mark.parametrize(
    ("charged", "other_lesson", "scope"),
    [
        (95_000, False, "thread"),
        (295_000, True, "day"),
    ],
)
async def test_budget_counts_prior_turns_and_refuses_the_next(
    client: httpx.AsyncClient, app: FastAPI, charged: int, other_lesson: bool, scope: str
) -> None:
    lesson = await seed(app)
    path = f"{API}/lessons/{lesson.lesson_id}/conversation"
    sent = await client.post(f"{path}/messages", json=question())
    sid = sent.json()["session_id"]
    await wait_status(client, sid, "completed")
    async with app.state.session_factory() as db:
        session = await db.get(AgentSession, sid)
        call_row = await db.scalar(select(LlmCall).where(LlmCall.session_id == sid))
        pending = await db.get(Lesson, lesson.pending_id)
        assert session is not None and pending is not None and call_row is not None
        session.tokens_in, session.tokens_out = charged, 0
        call_row.tokens_in, call_row.tokens_out = charged, 0
        pending.status = "ready"
        await db.commit()
    usage = (await client.get(path)).json()["usage"]
    assert usage["thread_tokens"] == usage["day_tokens"] == charged
    target = lesson.pending_id if other_lesson else lesson.lesson_id
    rejected_path = f"{API}/lessons/{target}/conversation"
    refused = await client.post(f"{rejected_path}/messages", json=question())
    assert refused.status_code == 429
    assert refused.json()["error"]["code"] == "conversation_budget_reached"
    assert refused.json()["error"]["details"] == {"scope": scope}
    if other_lesson:
        assert (await client.get(rejected_path)).json() is None
