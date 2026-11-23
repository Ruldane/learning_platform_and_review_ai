from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select

from app.db.models.mcp import McpChange
from tests.features.brain.conftest import brain_citations  # noqa: F401
from tests.mcp.adapter_support import call
from tests.mcp.support import API, LOCAL, Mcp
from tests.sessions_support import wait_status


@pytest.mark.usefixtures("brain_citations")
async def test_mcp_wipe_requires_confirmation_and_erases_undo_snapshots(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    client.headers.update(LOCAL)
    mcp = Mcp(client)
    token = await mcp.token(("brain", "conversations"), "write")
    opened, failed = await call(mcp, token, "brain_create_conversation", {})
    assert not failed, opened
    thread_id = opened["data"]["id"]
    sent, failed = await call(
        mcp,
        token,
        "brain_ask_librarian",
        {
            "conversation_id": thread_id,
            "request_id": str(uuid4()),
            "question": "Question privée sur un astre.",
        },
    )
    assert not failed, sent
    await wait_status(client, sent["data"]["session_id"], "completed")
    pending, failed = await call(mcp, token, "conversations_wipe", {"scope": "brain"})
    assert not failed, pending
    assert pending["data"]["status"] == "pending_confirmation"
    async with app.state.session_factory() as db:
        assert await db.scalar(
            select(McpChange).where(McpChange.table_name == "conversation_turns").limit(1)
        )
    assert len((await client.get(f"{API}/conversations/brain")).json()) == 1

    confirm = pending["data"]["confirmation_id"]
    checked = await client.post(f"{API}/mcp/confirmations/{confirm}/confirm")
    assert checked.status_code == 200, checked.text
    assert checked.json()["status"] == "confirmed", checked.text
    assert (await client.get(f"{API}/conversations/brain")).json() == []
    async with app.state.session_factory() as db:
        assert (await db.scalars(select(McpChange))).all() == []


async def test_mcp_can_change_training_mode_without_a_confirmation(
    client: httpx.AsyncClient,
) -> None:
    client.headers.update(LOCAL)
    mcp = Mcp(client)
    token = await mcp.token(("study",), "write")
    created, failed = await call(
        mcp, token, "study_start_training", {"new_conversation": True, "mode": "direct"}
    )
    assert not failed, created
    study_id = created["data"]["id"]
    changed, failed = await call(
        mcp,
        token,
        "study_update_training_context",
        {"study_session_id": study_id, "body": {"action": "mode", "mode": "feynman"}},
    )
    assert not failed, changed
    reread = await client.get(f"{API}/study-sessions/training/{study_id}")
    assert reread.json()["mode"] == "feynman"
    assert (await client.get(f"{API}/mcp/confirmations")).json() == []
