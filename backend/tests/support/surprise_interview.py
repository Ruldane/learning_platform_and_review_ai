from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from fastapi import FastAPI

from app.features.message_review.service import telegram_connection
from app.features.surprise_interview.repository import SettingsRepository
from app.features.surprise_interview.schedule import due_week
from tests.agents.graphs.interview_support import debrief_json, plan_json, turn_json
from tests.mcp.adapter_support import call
from tests.mcp.support import API, Mcp
from tests.support.telegram_review import CHAT, configure, telegram_token

SETTINGS = f"{API}/surprise-interviews/settings"
MONDAY = datetime(2026, 11, 23, 17, 59, tzinfo=UTC)
SCRIPT = [
    plan_json(count=3),
    *(turn_json(note=4, follow_up="Une relance que le mode bref doit écarter ?") for _ in range(3)),
    debrief_json(),
]


async def configure_pair(client: httpx.AsyncClient) -> str:
    cards = await telegram_token(client)
    assert (await configure(client, cards["id"])).status_code == 200
    created = await client.post(
        f"{API}/mcp/tokens",
        json={"label": "Nod entretien", "features": ["surprise_interview"], "mode": "write"},
    )
    assert created.status_code == 201, created.text
    token = created.json()
    settings = await client.put(
        SETTINGS, json={"enabled": True, "token_id": token["id"], "role": "Ingénieure Python"}
    )
    assert settings.status_code == 200, settings.text
    return str(token["token"])


async def nod(client: httpx.AsyncClient, token: str, action: str, **kwargs: str) -> dict[str, Any]:
    envelope, failed = await call(
        Mcp(client), token, f"surprise_interview_{action}", {"chat_id": CHAT, **kwargs}
    )
    assert not failed, envelope
    return envelope["data"]


async def freeze_for_invite(app: FastAPI, user_id: str) -> None:
    """Positionne l'horloge sans épuiser la limite MCP utilisée par les parcours suivants."""
    async with app.state.session_factory() as db:
        prefs = await SettingsRepository(db, user_id).mine()
        link = await telegram_connection(db, user_id)
        assert prefs is not None and link is not None
        for offset in range(7):
            moment = MONDAY + timedelta(days=offset)
            if due_week(link, moment, prefs.consent_id) is not None:
                app.state.career.applications.now = lambda instant=moment: instant
                return
    raise AssertionError("Le créneau hebdomadaire ne produit aucune invitation.")


async def invitation(client: httpx.AsyncClient, app: FastAPI, token: str) -> str:
    user_id = str((await client.get(f"{API}/auth/me")).json()["id"])
    await freeze_for_invite(app, user_id)
    shown = await nod(client, token, "invite")
    return str(shown["invitation"]["id"])
