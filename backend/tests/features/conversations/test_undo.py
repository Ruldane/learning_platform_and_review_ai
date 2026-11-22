import asyncio

import httpx
import pytest
from fastapi import FastAPI

from app.providers.llm.fake import FakeChatModel
from tests.features.conversations.test_professor import API, question
from tests.features.lessons.test_router import seed
from tests.mcp.adapter_support import call
from tests.mcp.support import Mcp
from tests.mcp.test_direct_write import undo_last
from tests.sessions_support import wait_status
from tests.support.direct import claude  # noqa: F401


@pytest.mark.usefixtures("scripted_professor")
@pytest.mark.parametrize("finished", [False, True])
async def test_undo_mcp_removes_turn_before_or_after_the_reply(
    client: httpx.AsyncClient,
    app: FastAPI,
    monkeypatch: pytest.MonkeyPatch,
    claude: Mcp,  # noqa: F811
    finished: bool,
) -> None:
    lesson = await seed(app)
    path = f"{API}/lessons/{lesson.lesson_id}/conversation"
    at_model = asyncio.Event()
    stopped = asyncio.Event()
    original = FakeChatModel._astream

    async def blocking_stream(self: FakeChatModel, *args: object, **kwargs: object):
        at_model.set()
        try:
            await asyncio.Future()
        finally:
            stopped.set()
        async for chunk in original(self, *args, **kwargs):  # type: ignore[arg-type]
            yield chunk

    if not finished:
        monkeypatch.setattr(FakeChatModel, "_astream", blocking_stream)
    token = await claude.token(("sessions", "conversations"), "write")
    started, refused = await call(
        claude, token, "conversations_ask_professor", {"lesson_id": lesson.lesson_id, **question()}
    )
    assert not refused, started
    sid = started["data"]["session_id"]
    if finished:
        await wait_status(client, sid, "completed")
    else:
        async with asyncio.timeout(10):
            await at_model.wait()
    undone = await undo_last(claude)
    assert undone.status_code == 200, undone.text
    assert (await client.get(path)).json() is None
    if not finished:
        assert stopped.is_set()
        await wait_status(client, sid, "cancelled")
