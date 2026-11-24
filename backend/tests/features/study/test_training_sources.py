from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from tests.features.study.test_training import TRAINING
from tests.mcp.adapter_support import call
from tests.mcp.support import Mcp
from tests.sessions_support import wait_status
from tests.support.conversation_lessons import add_ready_lesson
from tests.support.direct import claude  # noqa: F401


@pytest.mark.parametrize("selected", [False, True])
async def test_training_uses_its_owners_lessons(
    client: httpx.AsyncClient,
    app: FastAPI,
    claude: Mcp,  # noqa: F811
    selected: bool,
) -> None:
    owner = app.state.local_user_id
    one = await add_ready_lesson(app, owner, "Vecteurs publics du premier programme.")
    two = await add_ready_lesson(app, owner, "Matrices publiques du deuxième programme.")
    await add_ready_lesson(
        app, "compte-tiers", "Vecteurs et matrices confidentiels du compte tiers."
    )
    opened = await client.post(TRAINING, json={"lesson_ids": [one]} if selected else {})
    path = f"{TRAINING}/{opened.json()['id']}"
    token = await claude.token(("sessions", "conversations"), "write")
    for topic, expected in (("Vecteurs", one), ("Matrices", one if selected else two)):
        sent = await client.post(
            f"{path}/messages",
            json={"request_id": str(uuid4()), "question": topic},
            headers={"X-Tremplin-Run": "codex"},
        )
        assert sent.status_code == 202, sent.text
        sid = sent.json()["session_id"]
        await wait_status(client, sid, "waiting_user")
        brief, refused = await call(claude, token, "agents_play_brief", {"session_id": sid})
        assert not refused, brief
        messages = " ".join(m["content"] for m in brief["data"]["messages"])
        cited_topic = "Vecteurs" if selected else topic
        assert f'[1] <<<CONTENU_NON_FIABLE source="reference">>>\n{cited_topic} publi' in messages
        if selected:
            assert "Matrices publiques du deuxième programme" not in messages
        assert "confidentiels du compte tiers" not in messages
        accepted, refused = await call(
            claude,
            token,
            "agents_play_submit",
            {
                "session_id": sid,
                "step_id": brief["data"]["step_id"],
                "response": "On travaille [1].",
            },
        )
        assert not refused, accepted
        await wait_status(client, sid, "completed")
        turn = (await client.get(path)).json()["conversation"]["turns"][-1]
        assert [source["id"] for source in turn["sources"]] == [expected]
