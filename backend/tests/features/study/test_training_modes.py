from uuid import uuid4

import httpx

from tests.features.study.test_training import TRAINING
from tests.mcp.adapter_support import call
from tests.mcp.support import Mcp
from tests.sessions_support import wait_status
from tests.support.direct import claude  # noqa: F401


async def _played_turn(
    client: httpx.AsyncClient, mcp: Mcp, token: str, args: dict[str, str], reply: str
) -> tuple[str, str]:
    started, refused = await call(
        mcp,
        token,
        "agents_play_start",
        {"launch": "study_talk_training", "played_by": "codex", "arguments": args},
    )
    assert not refused, started
    sid = started["data"]["session_id"]
    await wait_status(client, sid, "waiting_user")
    brief, refused = await call(mcp, token, "agents_play_brief", {"session_id": sid})
    assert not refused and brief["data"]["agent"] == "training_tutor"
    messages = " ".join(m["content"] for m in brief["data"]["messages"])
    submitted, refused = await call(
        mcp,
        token,
        "agents_play_submit",
        {"session_id": sid, "step_id": brief["data"]["step_id"], "response": reply},
    )
    assert not refused, submitted
    await wait_status(client, sid, "completed")
    return sid, messages


async def test_training_mode_changes_the_following_turn_without_restarting(
    client: httpx.AsyncClient,
    claude: Mcp,  # noqa: F811
) -> None:
    opened = await client.post(TRAINING, json={})
    study_id = opened.json()["id"]
    path = f"{TRAINING}/{study_id}"
    token = await claude.token(("sessions", "conversations", "study"), "write")
    for index, (mode, instruction) in enumerate(
        [
            ("socratic", "questions progressives"),
            ("feynman", "avec ses propres mots"),
            ("direct", "explique directement"),
        ]
    ):
        changed = await client.patch(path, json={"action": "mode", "mode": mode})
        assert changed.status_code == 200 and changed.json()["mode"] == mode
        args = {"study_session_id": study_id, "request_id": str(uuid4()), "question": "Pourquoi ?"}
        sid, messages = await _played_turn(
            client, claude, token, args, f"Question suivante {index}."
        )
        assert instruction in messages
        if index:
            assert f"Question suivante {index - 1}." in messages
        duplicate = await client.post(
            f"{path}/messages",
            json={
                "request_id": args["request_id"],
                "question": args["question"],
            },
        )
        assert duplicate.status_code == 202 and duplicate.json()["session_id"] == sid
        actual = (await client.get(path)).json()
        assert actual["conversation"]["id"] == study_id
        assert len(actual["conversation"]["turns"]) == index + 1


async def test_cancel_revokes_the_active_turn_and_frees_the_study_slot(
    client: httpx.AsyncClient,
) -> None:
    opened = await client.post(TRAINING, json={})
    path = f"{TRAINING}/{opened.json()['id']}"
    sent = await client.post(
        f"{path}/messages",
        json={"request_id": str(uuid4()), "question": "Commençons le training."},
        headers={"X-Tremplin-Run": "codex"},
    )
    assert sent.status_code == 202
    sid = sent.json()["session_id"]
    await wait_status(client, sid, "waiting_user")
    busy = await client.patch(path, json={"action": "finish", "worked_minutes": 5})
    assert busy.status_code == 409 and busy.json()["error"]["code"] == "conversation_busy"
    stopped = await client.patch(path, json={"action": "cancel"})
    assert stopped.is_success and stopped.json()["status"] == "cancelled"
    assert stopped.json()["minutes"] == 0
    await wait_status(client, sid, "cancelled")
    assert (await client.get(f"{TRAINING}/open")).json() is None
    assert (await client.post(TRAINING, json={})).status_code == 202
