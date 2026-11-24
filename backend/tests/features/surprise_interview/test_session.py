import httpx
import pytest
from fastapi import FastAPI

from tests.agents.graphs.interview_support import question_text
from tests.features.applications.interview_support import add_profile
from tests.mcp.adapter_support import call
from tests.mcp.support import API, Mcp
from tests.sessions_support import use_test_runtime, wait_status
from tests.support.surprise_interview import SCRIPT, configure_pair, invitation, nod
from tests.support.telegram_review import CHAT


@pytest.fixture
def scripted_surprise(monkeypatch: pytest.MonkeyPatch) -> None:
    use_test_runtime(monkeypatch, SCRIPT)


@pytest.mark.usefixtures("scripted_surprise")
async def test_nod_resumes_the_exact_question_and_returns_a_three_answer_debrief(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    await add_profile(app)
    token = await configure_pair(client)
    invite = await invitation(client, app, token)
    assert (await client.get(f"{API}/interviews")).json() == []
    started = await nod(client, token, "accept", invitation_id=invite)
    assert (await nod(client, token, "accept", invitation_id=invite)) == started
    session_id = started["session_id"]
    for number in range(1, 4):
        session = await wait_status(client, session_id, "waiting_user")
        state = await nod(client, token, "state", invitation_id=invite)
        question = state["question"]
        assert state["status"] == "question" and state["debrief"] is None
        assert question["id"] == session["pending_interrupt"]["interrupt_id"]
        assert question_text(number) in str(question["text"])
        assert (await nod(client, token, "state", invitation_id=invite)) == state
        body = {
            "invitation_id": invite,
            "question_id": question["id"],
            "message_id": str(number),
            "answer": f"Ma réponse technique à la question {number}.",
        }
        received, error = await call(
            Mcp(client), token, "surprise_interview_answer", {"chat_id": CHAT, **body}
        )
        assert not error and received["data"] == {"received": True}
        assert "ne pourra pas être annulé" in received["notice"]
        assert (await nod(client, token, "answer", **body)) == {"received": True}
    await wait_status(client, session_id, "completed")
    final = await nod(client, token, "state", invitation_id=invite)
    assert final["status"] == "done" and final["debrief"]["scores"]["clarity"] == 4
    saved = (await client.get(f"{API}/interviews/{started['interview_id']}")).json()
    assert len(saved["exchanges"]) == 3
    assert all(exchange["follow_up"] is None for exchange in saved["exchanges"])


@pytest.mark.usefixtures("scripted_surprise")
async def test_nod_rejects_an_answer_when_the_interview_is_cancelled_before_resume(
    client: httpx.AsyncClient, app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    await add_profile(app)
    token = await configure_pair(client)
    invite = await invitation(client, app, token)
    started = await nod(client, token, "accept", invitation_id=invite)
    session_id = started["session_id"]
    session = await wait_status(client, session_id, "waiting_user")
    runner = app.state.runtime.runner
    resume = runner.resume

    async def cancel_first(user_id: str, sid: str, question_id: str, value: object) -> None:
        await runner.cancel(user_id, sid)
        await resume(user_id, sid, question_id, value)

    monkeypatch.setattr(runner, "resume", cancel_first)
    body = {
        "chat_id": CHAT,
        "invitation_id": invite,
        "question_id": session["pending_interrupt"]["interrupt_id"],
        "message_id": "1",
        "answer": "Une réponse concurrente de l’annulation.",
    }
    for _ in range(2):
        received, error = await call(Mcp(client), token, "surprise_interview_answer", body)
        assert error and received["data"]["error"]["code"] == "surprise_question_changed"
    await wait_status(client, session_id, "cancelled")
