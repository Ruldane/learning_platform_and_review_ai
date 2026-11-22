import asyncio
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import FastAPI

from tests.mcp.adapter_support import call as call_tool
from tests.mcp.support import API, Mcp
from tests.support.telegram_review import (
    CHAT,
    MOMENT,
    SETTINGS,
    add_card,
    configure,
    telegram_token,
)


async def call(
    nod: Mcp, token: str, tool: str, arguments: dict[str, Any]
) -> tuple[dict[str, Any], bool]:
    envelope, failed = await call_tool(nod, token, tool, arguments)
    return envelope.get("data", {}), failed


async def test_nod_replays_one_daily_question_and_applies_only_one_rating(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    defaults = await client.get(SETTINGS)
    assert (defaults.status_code, defaults.json().get("enabled")) == (200, False)
    token = await telegram_token(client)
    await add_card(app, app.state.local_user_id)
    nod = Mcp(client)
    settings = await configure(client, token["id"])
    assert settings.status_code == 200 and settings.json()["timezone"] == "Europe/Paris"
    app.state.quiz.now = lambda: datetime(2026, 11, 23, 16, 59, tzinfo=UTC)
    pending, error = await call(nod, token["token"], "message_review_claim", {"chat_id": CHAT})
    assert not error and pending["challenge"] is None
    app.state.quiz.now = lambda: MOMENT
    claims = await asyncio.gather(
        *(call(nod, token["token"], "message_review_claim", {"chat_id": CHAT}) for _ in range(2))
    )
    assert all(not failed for _, failed in claims)
    challenge, repeat = [claim["challenge"] for claim, _ in claims]
    assert challenge == repeat and "À quoi sert un index ?" in str(challenge["question"])
    assert "answer" not in challenge
    where = {"chat_id": CHAT, "challenge_id": challenge["id"]}
    reveal, error = await call(nod, token["token"], "message_review_reveal", where)
    assert not error and "Il repère des valeurs." in str(reveal["answer"])
    reply = {**where, "result": "ok"}
    ratings = await asyncio.gather(
        *(call(nod, token["token"], "message_review_answer", reply) for _ in range(2))
    )
    assert all(not failed for _, failed in ratings)
    result, replay = [data for data, _ in ratings]
    assert result == replay and result["step"] == 2
    _, conflict = await call(
        nod, token["token"], "message_review_answer", {**reply, "result": "fail"}
    )
    assert conflict

    history = (await client.get(f"{API}/mcp/changes")).json()
    call_id = history[0]["call_id"]
    assert (await client.post(f"{API}/mcp/changes/{call_id}/undo")).status_code == 200
    queue = (await client.get(f"{API}/flashcards/due")).json()
    assert len(queue["cards"]) == 1 and queue["reviewed_today"] == 0
