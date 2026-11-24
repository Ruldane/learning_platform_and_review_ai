import json
from uuid import uuid4

import httpx
from fastapi import FastAPI

from tests.features.applications.test_system_design import REVIEW, save_rectangle
from tests.features.lessons.test_router import seed
from tests.mcp.adapter_support import call
from tests.mcp.support import API, Mcp
from tests.sessions_support import wait_status


async def launch_played(claude: Mcp, token: str, tool: str, arguments: dict[str, str]) -> str:
    started, refused = await call(
        claude,
        token,
        "agents_play_start",
        {
            "launch": tool,
            "played_by": "codex",
            "arguments": arguments,
        },
    )
    assert not refused, started
    return str(started["data"]["session_id"])


async def submit_played(claude: Mcp, token: str, sid: str, step: str, response: str) -> None:
    result, refused = await call(
        claude,
        token,
        "agents_play_submit",
        {"session_id": sid, "step_id": step, "response": response},
    )
    assert not refused, result


async def test_played_feynman_uses_english_and_records_the_assessment(
    claude: Mcp, app: FastAPI, client: httpx.AsyncClient
) -> None:
    lesson = await seed(app)
    token = await claude.token(("sessions", "conversations"), "write")
    sid = await launch_played(
        claude,
        token,
        "conversations_explain_lesson",
        {"lesson_id": lesson.lesson_id, "request_id": str(uuid4())},
    )
    question = (await wait_status(client, sid, "waiting_user"))["pending_interrupt"]
    assert question["kind"] == "feynman_explanation"
    assert (
        question["question"] == "Can you explain the topic in your own words and give an example?"
    )
    assert question["fields"][0]["label"] == "Your explanation"
    explanation = "Les deux étapes forment une chaîne."
    resumed = await client.post(
        f"{API}/sessions/{sid}/resume",
        json={
            "interrupt_id": question["interrupt_id"],
            "value": {"answers": {"answer": explanation}},
        },
    )
    assert resumed.status_code == 202, resumed.text
    await wait_status(client, sid, "waiting_user")
    brief, refused = await call(claude, token, "agents_play_brief", {"session_id": sid})
    assert not refused and brief["data"]["agent"] == "training_tutor"
    prompt = "\n".join(message["content"] for message in brief["data"]["messages"])
    assert "Reference:" in prompt and "Explanation:" in prompt and explanation in prompt
    await submit_played(
        claude,
        token,
        sid,
        brief["data"]["step_id"],
        json.dumps({"summary": "You explained the chain.", "mastered": True}),
    )
    await wait_status(client, sid, "completed")
    report = (await client.get(f"{API}/lessons/{lesson.lesson_id}/explain")).json()["report"]
    assert report["explanation"] == explanation
    assert report["summary"] == "You explained the chain."


async def test_played_classroom_runs_each_role_and_saves_the_replies(
    claude: Mcp, app: FastAPI, client: httpx.AsyncClient
) -> None:
    lesson = await seed(app)
    token = await claude.token(("sessions", "conversations"), "write")
    sid = await launch_played(
        claude,
        token,
        "conversations_ask_classroom",
        {
            "lesson_id": lesson.lesson_id,
            "request_id": str(uuid4()),
            "question": "The two steps form a chain.",
        },
    )
    classmates = [
        ("beginner", "You are discovering the topic", "Which step comes first?"),
        ("peer", "You have a comparable level", "The second step uses the first result."),
        ("advanced", "Propose an edge case", "What happens when a result is missing?"),
    ]
    for _, instruction, reply in classmates:
        await wait_status(client, sid, "waiting_user")
        brief, refused = await call(claude, token, "agents_play_brief", {"session_id": sid})
        assert not refused and brief["data"]["agent"] == "training_tutor"
        assert instruction in brief["data"]["messages"][0]["content"]
        await submit_played(claude, token, sid, brief["data"]["step_id"], reply)
    await wait_status(client, sid, "completed")
    room = (await client.get(f"{API}/lessons/{lesson.lesson_id}/classroom")).json()
    assert room["turns"][0]["classmates"] == [
        {"role": role, "answer": reply} for role, _, reply in classmates
    ]


async def test_played_system_design_assesses_the_submitted_board(
    claude: Mcp, client: httpx.AsyncClient
) -> None:
    started = await client.post(
        f"{API}/interviews",
        json={"mode": "case", "duration_min": 30, "system_design": True},
        headers={"X-Tremplin-Run": "codex"},
    )
    assert started.status_code == 202, started.text
    sid = started.json()["session_id"]
    path = f"{API}/interviews/{started.json()['interview_id']}/design"
    question = (await wait_status(client, sid, "waiting_user"))["pending_interrupt"]
    assignment = (await client.get(path)).json()
    version = await save_rectangle(client, assignment["board"]["id"], "Reminder queue")
    await save_rectangle(client, version, "Later draft")
    resumed = await client.post(
        f"{API}/sessions/{sid}/resume",
        json={
            "interrupt_id": question["interrupt_id"],
            "value": {"board_id": version, "defense": "The queue absorbs traffic spikes."},
        },
    )
    assert resumed.status_code == 202, resumed.text
    token = await claude.token(("sessions", "applications"), "write")
    await wait_status(client, sid, "waiting_user")
    brief, refused = await call(claude, token, "agents_play_brief", {"session_id": sid})
    assert not refused and brief["data"]["agent"] == "interviewer"
    prompt = "\n".join(message["content"] for message in brief["data"]["messages"])
    assert "Reminder queue" in prompt and "Later draft" not in prompt
    await submit_played(claude, token, sid, brief["data"]["step_id"], json.dumps(REVIEW))
    await wait_status(client, sid, "completed")
    report = (await client.get(path)).json()
    assert report["board"]["id"] == version
    assert report["review"]["summary"] == REVIEW["summary"] and report["proof_saved"] is True
