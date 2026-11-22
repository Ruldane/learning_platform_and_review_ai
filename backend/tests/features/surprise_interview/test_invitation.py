from datetime import UTC, datetime, timedelta

import httpx
from fastapi import FastAPI

from tests.mcp.adapter_support import call
from tests.mcp.support import API, Mcp
from tests.support.telegram_review import CHAT, configure, telegram_token

SETTINGS = f"{API}/surprise-interviews/settings"
MONDAY = datetime(2026, 11, 23, 17, 59, tzinfo=UTC)


async def test_invitation_requires_separate_consent_and_is_reserved_once(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    default = await client.get(SETTINGS)
    assert default.status_code == 200 and not default.json()["enabled"]
    review_token = await telegram_token(client)
    assert (await configure(client, review_token["id"])).status_code == 200
    created = await client.post(
        f"{API}/mcp/tokens",
        json={"label": "Nod entretien", "features": ["surprise_interview"], "mode": "write"},
    )
    assert created.status_code == 201, created.text
    token = created.json()
    fake_nod = Mcp(client)
    args = {"chat_id": CHAT}
    _, denied = await call(fake_nod, token["token"], "surprise_interview_invite", args)
    assert denied
    consent = await client.put(
        SETTINGS, json={"enabled": True, "token_id": token["id"], "role": "Ingénieure Python"}
    )
    assert consent.status_code == 200 and consent.json()["timezone"] == "Europe/Paris"
    app.state.career.applications.now = lambda: MONDAY.replace(hour=16)
    outside, failed = await call(fake_nod, token["token"], "surprise_interview_invite", args)
    assert not failed and outside["data"]["invitation"] is None

    invitations = []
    for offset in range(7):
        moment = MONDAY + timedelta(days=offset)
        app.state.career.applications.now = lambda instant=moment: instant
        candidate, failed = await call(fake_nod, token["token"], "surprise_interview_invite", args)
        assert not failed
        if invite := candidate["data"]["invitation"]:
            invitations.append(invite)
            again, replay_failed = await call(
                fake_nod, token["token"], "surprise_interview_invite", args
            )
            assert not replay_failed and again["data"]["invitation"] == invite
    assert len(invitations) == 1
    assert (await client.get(f"{API}/interviews")).json() == []
