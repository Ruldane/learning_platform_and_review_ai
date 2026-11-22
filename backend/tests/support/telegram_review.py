from datetime import UTC, date, datetime
from typing import Any

import httpx
from fastapi import FastAPI

from app.db.models.study import Flashcard
from tests.mcp.support import API, LOCAL, Mcp

SETTINGS = f"{API}/message-reviews/settings"
CHAT = "55001424"
MOMENT = datetime(2026, 11, 23, 17, 30, tzinfo=UTC)


async def add_card(app: FastAPI, user_id: str) -> str:
    async with app.state.session_factory() as db:
        card = Flashcard(
            user_id=user_id,
            front="À quoi sert un index ?",
            back="Il repère des valeurs.",
            front_hash="index-recette",
            source="lesson",
            step=1,
            due_date=date(2026, 11, 23),
        )
        db.add(card)
        await db.commit()
        return card.id


async def telegram_token(client: httpx.AsyncClient, *, label: str = "Nod") -> dict[str, Any]:
    client.headers.update(LOCAL)
    await Mcp(client).enable()
    token = await client.post(
        f"{API}/mcp/tokens",
        json={"label": label, "features": ["message_review"], "mode": "write"},
    )
    assert token.status_code == 201, token.text
    return token.json()


async def configure(client: httpx.AsyncClient, token_id: str) -> httpx.Response:
    return await client.put(
        SETTINGS,
        json={
            "enabled": True,
            "token_id": token_id,
            "chat_id": CHAT,
            "start": "18:00",
            "end": "19:00",
        },
    )
